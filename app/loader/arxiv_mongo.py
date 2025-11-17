from __future__ import annotations
import json
import logging
import os
from pathlib import Path
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError
import time  # 추가: time 모듈 import

from app.db.connection import get_mongo_collection, get_mongo_collection_for_search
from app.core.settings import settings
from app.loader.arxiv_category import parse_categories

logger = logging.getLogger("uvicorn.error")

# 데이터 파일 경로
BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = BACKEND_ROOT / "data"
DATA_DIR = Path(os.getenv("DATA_DIR", str(DEFAULT_DATA_DIR)))
DATA_FILE_PATH = Path(os.getenv("ARXIV_FILE", str(DATA_DIR / "arxiv-metadata-oai-snapshot.json")))

BATCH_SIZE = int(os.getenv("ARXIV_BATCH_SIZE", "1000"))
PROGRESS_EVERY = int(os.getenv("ARXIV_PROGRESS_EVERY", "5000"))

def ingest_arxiv_to_mongo() -> bool:
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
        with open(DATA_FILE_PATH, "r", encoding="utf-8") as f:
            total_lines = sum(1 for _ in f)
            f.seek(0)

            start_t = time.time()
            batch: list[UpdateOne] = []
            for i, line in enumerate(f):
                if not line.strip():
                    continue
                doc = json.loads(line)
                codes = parse_categories(doc.get("categories"))
                doc["categories"] = codes  # 변경: categories를 배열로 설정 (기존 문자열 대체)
                # doc["categories_codes"] = codes  # 제거: 불필요 (categories로 통합)
                upsert = UpdateOne({"id": doc["id"]}, {"$set": doc}, upsert=True)
                batch.append(upsert)

                if len(batch) >= BATCH_SIZE:
                    try:
                        collection.bulk_write(batch, ordered=False)
                        logger.info(f"[arxiv-job] upserted {len(batch)} records")
                    except BulkWriteError as bwe:
                        logger.warning(f"[arxiv-job] BulkWriteError: {bwe.details}")
                        for e in bwe.details.get("writeErrors", []):
                            if failures_collection:
                                failures_collection.insert_one({"id": e.get("op", {}).get("id")})
                    except Exception as e:
                        logger.error(f"[arxiv-job] unexpected bulk_write error: {e}")
                    batch.clear()

                if (i + 1) % PROGRESS_EVERY == 0:
                    logger.info(f"[arxiv-job] processed {i + 1}/{total_lines} lines")

            if batch:
                try:
                    collection.bulk_write(batch, ordered=False)
                    logger.info(f"[arxiv-job] upserted {len(batch)} records")
                except BulkWriteError as bwe:
                    logger.warning(f"[arxiv-job] BulkWriteError: {bwe.details}")
                    for e in bwe.details.get("writeErrors", []):
                        if failures_collection:
                            failures_collection.insert_one({"id": e.get("op", {}).get("id")})
                except Exception as e:
                    logger.error(f"[arxiv-job] unexpected bulk_write error: {e}")

        took = time.time() - start_t
        logger.info(f"[arxiv-job] data load complete in {took:.1f}s")
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