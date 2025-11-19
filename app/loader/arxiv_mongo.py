from __future__ import annotations
import json
import logging
import os
from pathlib import Path
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError

from app.db.mongodb import get_mongo_client_direct
from app.core.settings import settings
from app.loader.arxiv_category import parse_categories
from app.seed.categories_seed import seed_categories_from_codes
from app.loader.config import DATA_FILE_PATH, BATCH_SIZE, PROGRESS_EVERY
from app.loader.utils import get_current_time

logger = logging.getLogger(__name__)

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
    logger.info(f"[arxiv-job] read_and_parse_data: 시작, 파일={data_file_path}")
    with open(data_file_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
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
            if (i + 1) % 10000 == 0:
                logger.info(f"[arxiv-job] read_and_parse_data: {i + 1} lines parsed")
    logger.info(f"[arxiv-job] read_and_parse_data: 완료, 총 {len(ops)} ops 생성")
    return ops

def batch_insert_documents(collection, failures_collection, ops: list[UpdateOne], batch_size: int, progress_every: int) -> int:
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
        try:
            seed_categories_from_codes(list(unique_codes))
        except Exception as e:
            logger.error(f"[arxiv-job] category seeding failed: {e}")

def ingest_arxiv_to_mongo() -> bool:
    """
    arXiv 데이터를 MongoDB에 적재.
    """
    try:
        client = get_mongo_client_direct()
    except RuntimeError as e:
        logger.error(f"[arxiv-job] MongoDB not initialized: {e}")
        return False

    db = client[settings.mongo_db]
    collection = db[settings.mongo_collection]
    failures_collection = db["arxiv_failures"]
    logger.info(f"[arxiv-job] MongoDB collection: {collection.full_name}")

    try:
        logger.info("[arxiv-job] 인덱스 생성 시작")
        # 기존 인덱스
        collection.create_index("id", unique=True)
        # 검색 성능 향상용 인덱스 추가
        collection.create_index("title")
        collection.create_index("abstract")
        collection.create_index("authors")
        collection.create_index("categories")
        collection.create_index([("categories", 1), ("update_date", -1)])
        logger.info("[arxiv-job] 인덱스 생성 완료")
    except Exception as e:
        logger.debug(f"Index create skipped (categories): {e}")

    if os.getenv("ARXIV_REMOVE_OLD_DATA"):
        logger.info("[arxiv-job] removing old data")
        collection.delete_many({})

    try:
        logger.info("[arxiv-job] 데이터 파싱 시작")
        ops = read_and_parse_data(DATA_FILE_PATH)
        logger.info("[arxiv-job] 데이터 파싱 완료, 적재 시작")
        processed = batch_insert_documents(collection, failures_collection, ops, BATCH_SIZE, PROGRESS_EVERY)
        logger.info(f"[arxiv-job] data load complete total={processed}")
        seed_categories_from_mongo(collection)
        return True
    except FileNotFoundError:
        logger.error(f"[arxiv-job] file not found: {DATA_FILE_PATH}")
    except json.JSONDecodeError as e:
        logger.error(f"[arxiv-job] JSON decode error: {e}")
    except Exception as e:
        logger.error(f"[arxiv-job] unexpected error: {e}")
    return False

def copy_prod_to_local_mongo() -> bool:
    """
    Production MongoDB에서 로컬로 데이터 복제.
    Note: 현재 구현은 동일한 클라이언트를 사용하므로 실제로는 동작하지 않음.
    이 함수는 별도의 prod/local 설정이 필요합니다.
    """
    try:
        client = get_mongo_client_direct()
    except RuntimeError as e:
        logger.error(f"[arxiv-job] MongoDB not initialized: {e}")
        return False

    # TODO: prod와 local을 구분하려면 별도의 연결 설정이 필요
    # 현재는 동일한 클라이언트를 사용
    db = client[settings.mongo_db]
    local_coll = db[settings.mongo_collection]

    logger.info("[arxiv-job] copying arxiv_papers from prod to local mongo")
    logger.warning("[arxiv-job] WARNING: prod and local are the same instance")
    
    try:
        # 실제 복제 로직은 prod 연결이 별도로 설정된 경우에만 의미가 있음
        # 현재는 카테고리 시딩만 수행
        seed_categories_from_mongo(local_coll)
        logger.info("[arxiv-job] category seeding complete")
        return True
    except Exception as e:
        logger.error(f"[arxiv-job] copy failed: {e}")
        return False