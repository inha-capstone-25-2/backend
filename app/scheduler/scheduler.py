from __future__ import annotations
import json
import logging
import os
from pathlib import Path
from pymongo import UpdateOne
from pymongo.errors import PyMongoError, BulkWriteError

from app.db.connection import get_mongo_collection

logger = logging.getLogger("uvicorn.error")  # FastAPI 기본 콘솔 출력 로거 사용

# 데이터 파일 경로
BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = BACKEND_ROOT / "data"
DATA_DIR = Path(os.getenv("DATA_DIR", str(DEFAULT_DATA_DIR)))
DATA_FILE_PATH = Path(os.getenv("ARXIV_FILE", str(DATA_DIR / "arxiv-metadata-oai-snapshot.json")))

BATCH_SIZE = int(os.getenv("ARXIV_BATCH_SIZE", "1000"))
PROGRESS_EVERY = int(os.getenv("ARXIV_PROGRESS_EVERY", "5000"))

DATASET = "Cornell-University/arxiv"
FILENAME = "arxiv-metadata-oai-snapshot.json"


def download_arxiv_snapshot() -> bool:
    """
    arxiv-metadata-oai-snapshot.json을 Kaggle에서 다운로드 및 압축해제.
    - KAGGLE_USERNAME/KAGGLE_KEY 또는 ~/.kaggle/kaggle.json 필요
    - 성공 시 True, 실패 시 False
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if DATA_FILE_PATH.exists():
        return True
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi

        api = KaggleApi()
        api.authenticate()
        api.dataset_download_files(DATASET, path=str(DATA_DIR), unzip=True, quiet=True)
        # 남은 zip 정리
        for z in DATA_DIR.glob("*.zip"):
            try:
                z.unlink()
            except OSError:
                pass
        if not DATA_FILE_PATH.exists():
            logger.error("Downloaded but target JSON not found.")
            return False
        logger.info("Downloaded arXiv snapshot from Kaggle.")
        return True
    except Exception as e:
        logger.error(f"Kaggle download failed: {e}")
        return False


def load_arxiv_data_to_mongodb() -> bool:
    """
    내부 스케줄러/API가 호출하는 Mongo 적재 작업.
    """
    logger.info("[arxiv-job] start")

    if not DATA_FILE_PATH.exists():
        if not download_arxiv_snapshot():
            logger.error(f"Data file unavailable: {DATA_FILE_PATH}")
            return False

    client, collection = get_mongo_collection()
    if collection is None:
        logger.error("Mongo collection unavailable.")
        if client:
            client.close()
        return False

    try:
        collection.create_index("id", unique=True)
    except Exception as e:
        logger.debug(f"Index create skipped: {e}")

    processed = 0
    ops: list[UpdateOne] = []

    try:
        with DATA_FILE_PATH.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                _id = data.get("id")
                if not _id:
                    continue

                doc = {
                    "id": _id,
                    "title": data.get("title"),
                    "authors": data.get("authors"),
                    "abstract": data.get("abstract"),
                    "categories": data.get("categories"),
                    "update_date": data.get("update_date"),
                }
                doc = {k: v for k, v in doc.items() if v is not None}

                ops.append(UpdateOne({"id": _id}, {"$set": doc}, upsert=True))
                processed += 1

                if len(ops) >= BATCH_SIZE:
                    collection.bulk_write(ops, ordered=False)
                    ops.clear()
                    logger.info(f"[arxiv-job] processed={processed} (batch flush)")

                if processed and processed % PROGRESS_EVERY == 0:
                    logger.info(f"Processed {processed} records...")

        if ops:
            collection.bulk_write(ops, ordered=False)

        logger.info(f"[arxiv-job] complete total={processed}")
        return True
    except (PyMongoError, BulkWriteError) as e:
        logger.error(f"[arxiv-job] mongo bulk write error: {e}")
        return False
    except FileNotFoundError:
        logger.error(f"[arxiv-job] file missing: {DATA_FILE_PATH}")
        return False
    except Exception as e:
        logger.error(f"[arxiv-job] unexpected error: {e}")
        return False
    finally:
        if client:
            client.close()
            logger.info("[arxiv-job] mongo client closed")
