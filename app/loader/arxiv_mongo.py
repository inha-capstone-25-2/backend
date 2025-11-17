from __future__ import annotations
import json
import logging
import os
from pathlib import Path
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError

from app.db.mongodb import get_mongo_collection, get_mongo_collection_for_search
from app.core.settings import settings
from app.loader.arxiv_category import parse_categories
from app.seed.categories_seed import seed_categories_from_codes
from app.loader.config import DATA_FILE_PATH, BATCH_SIZE, PROGRESS_EVERY
from app.loader.utils import get_current_time  # 추가

logger = logging.getLogger("uvicorn.error")

# 데이터 파일 경로
BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = BACKEND_ROOT / "data"
DATA_DIR = Path(os.getenv("DATA_DIR", str(DEFAULT_DATA_DIR)))
DATA_FILE_PATH = Path(os.getenv("ARXIV_FILE", str(DATA_DIR / "arxiv-metadata-oai-snapshot.json")))

def read_and_parse_data(data_file_path: Path) -> list[UpdateOne]:
    """
    JSON 파일을 읽어 UpdateOne 배치 리스트를 생성.
    """
    ops: list[UpdateOne] = []
    with open(data_file_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            _id = data.get("id")
            if not _id:
                continue

            codes = parse_categories(data.get("categories"))
            doc = {
                "id": _id,
                "title": data.get("title"),
                "authors": data.get("authors"),
                "abstract": data.get("abstract"),
                "categories": codes,
                "update_date": data.get("update_date"),
            }
            doc = {k: v for k, v in doc.items() if v is not None}
            ops.append(UpdateOne({"id": _id}, {"$set": doc}, upsert=True))
    return ops

def batch_insert_documents(collection, ops: list[UpdateOne], batch_size: int, progress_every: int) -> int:
    """
    배치 리스트를 MongoDB에 삽입.
    """
    processed = 0
    for i, op in enumerate(ops):
        if (i + 1) % batch_size == 0:
            try:
                collection.bulk_write(ops[i - batch_size + 1:i + 1], ordered=False)
                logger.info(f"[arxiv-job] upserted {batch_size} records")
            except BulkWriteError as bwe:
                logger.warning(f"[arxiv-job] BulkWriteError: {bwe.details}")
                for e in bwe.details.get("writeErrors", []):
                    if failures_collection:
                        failures_collection.insert_one({"id": e.get("op", {}).get("id")})
            except Exception as e:
                logger.error(f"[arxiv-job] unexpected bulk_write error: {e}")
        if (i + 1) % progress_every == 0:
            logger.info(f"[arxiv-job] processed {i + 1} records")
        processed += 1
    # 남은 배치 처리
    if ops:
        try:
            collection.bulk_write(ops, ordered=False)
            logger.info(f"[arxiv-job] upserted {len(ops)} records")
        except BulkWriteError as bwe:
            logger.warning(f"[arxiv-job] BulkWriteError: {bwe.details}")
            for e in bwe.details.get("writeErrors", []):
                if failures_collection:
                    failures_collection.insert_one({"id": e.get("op", {}).get("id")})
        except Exception as e:
            logger.error(f"[arxiv-job] unexpected bulk_write error: {e}")
    return processed

def seed_categories_from_mongo(collection) -> None:
    """
    MongoDB의 카테고리 코드를 기반으로 PostgreSQL 시드.
    """
    unique_codes = set()
    cursor = collection.find({}, {"categories": 1})
    for doc in cursor:
        if "categories" in doc and isinstance(doc["categories"], list):
            unique_codes.update(doc["categories"])
    cursor.close()
    
    if unique_codes:
        logger.info(f"[arxiv-job] seeding PostgreSQL categories from {len(unique_codes)} codes")
        seed_categories_from_codes(list(unique_codes))

def ingest_arxiv_to_mongo() -> bool:
    """
    arXiv 데이터를 MongoDB에 적재.
    """
    client, collection = get_mongo_collection()
    if collection is None:
        logger.error("[arxiv-job] Mongo collection unavailable")
        return False

    failures_collection = client[settings.mongo_db]["arxiv_failures"]
    logger.info(f"[arxiv-job] MongoDB collection: {collection.full_name}")

    try:
        collection.create_index("id", unique=True)
        collection.create_index("categories_codes")
        collection.create_index("categories_groups")
        collection.create_index([("categories_codes", 1), ("update_date", -1)])
    except Exception as e:
        logger.debug(f"Index create skipped (categories): {e}")

    if os.getenv("ARXIV_REMOVE_OLD_DATA"):
        logger.info("[arxiv-job] removing old data")
        collection.delete_many({})

    try:
        ops = read_and_parse_data(DATA_FILE_PATH)
        processed = batch_insert_documents(collection, ops, BATCH_SIZE, PROGRESS_EVERY)
        logger.info(f"[arxiv-job] data load complete total={processed}")
        
        seed_categories_from_mongo(collection)
        
        return True
    except FileNotFoundError:
        logger.error(f"[arxiv-job] file not found: {DATA_FILE_PATH}")
    except json.JSONDecodeError as e:
        logger.error(f"[arxiv-job] JSON decode error: {e}")
    except Exception as e:
        logger.error(f"[arxiv-job] unexpected error: {e}")
    finally:
        try:
            client.close()
        except Exception:
            pass
    return False

def copy_prod_to_local_mongo() -> bool:
    prod_client, prod_coll = get_mongo_collection_for_search()
    if prod_coll is None:
        logger.error("[arxiv-job] prod Mongo collection unavailable")
        return False

    local_client, local_coll = get_mongo_collection()
    if local_coll is None:
        logger.error("[arxiv-job] local Mongo collection unavailable")
        return False

    logger.info("[arxiv-job] copying arxiv_papers from prod to local mongo")
    try:
        local_coll.delete_many({})
        cursor = prod_coll.find({}, no_cursor_timeout=True)
        batch = []
        BATCH_SIZE = 1000
        count = 0
        for doc in cursor:
            doc.pop("_id", None)
            batch.append(doc)
            if len(batch) >= BATCH_SIZE:
                local_coll.insert_many(batch)
                count += len(batch)
                logger.info(f"[arxiv-job] copied {count} docs so far")
                batch.clear()
        if batch:
            local_coll.insert_many(batch)
            count += len(batch)
        logger.info(f"[arxiv-job] copy complete: total {count} docs")
        cursor.close()
        return True
    except Exception as e:
        logger.error(f"[arxiv-job] copy failed: {e}")
        return False
    finally:
        if prod_client:
            prod_client.close()
        if local_client:
            local_client.close()