import json
import logging
import os
from pymongo import UpdateOne
from pymongo.errors import PyMongoError, BulkWriteError
from dotenv import load_dotenv
from app.db.connection import get_mongo_collection

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 경로 설정 및 .env 로드
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(BACKEND_ROOT, "data")
DATA_FILE_PATH = os.path.join(DATA_DIR, "arxiv-metadata-oai-snapshot.json")
load_dotenv(os.path.join(BACKEND_ROOT, ".env"))

# 배치 설정
BATCH_SIZE = 1000
PROGRESS_EVERY = 5000


def download_and_unzip_dataset() -> bool:
    """Kaggle API로 데이터셋을 다운로드"""
    logger.info("Starting dataset download from Kaggle.")
    os.makedirs(DATA_DIR, exist_ok=True)

    if os.path.exists(DATA_FILE_PATH):
        logger.info(f"Dataset already exists at {DATA_FILE_PATH}. Skipping download.")
        return True

    try:
        os.environ.setdefault("KAGGLE_CONFIG_DIR", DATA_DIR)

        from kaggle.api.kaggle_api_extended import KaggleApi

        api = KaggleApi()
        api.authenticate()
        api.dataset_download_files(
            "Cornell-University/arxiv",
            path=DATA_DIR,
            unzip=True,
            quiet=True
        )

        # 남아 있는 zip 정리
        for fname in os.listdir(DATA_DIR):
            if fname.endswith(".zip"):
                try:
                    os.remove(os.path.join(DATA_DIR, fname))
                except OSError:
                    pass

        logger.info("Dataset downloaded and unzipped successfully via Kaggle API.")
        return True
    except Exception as e:
        logger.error(f"Failed to download dataset via Kaggle API: {e}")
        return False


def load_arxiv_data_to_mongodb():
    """arXiv 메타데이터 JSON 라인 파일을 MongoDB에 upsert."""
    logger.info("Starting arXiv data load job to MongoDB.")

    if not download_and_unzip_dataset():
        logger.error("Aborting data load job due to download failure.")
        return

    client, collection = get_mongo_collection()
    if collection is None:
        logger.error("Failed to get MongoDB collection. Aborting job.")
        if client:
            client.close()
        return

    try:
        ops = []
        count = 0
        with open(DATA_FILE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)

                    item = {
                        "id": data.get("id"),
                        "title": data.get("title"),
                        "authors": data.get("authors"),
                        "abstract": data.get("abstract"),
                        "categories": data.get("categories"),
                        "update_date": data.get("update_date"),
                    }
                    item = {k: v for k, v in item.items() if v is not None}

                    if item.get("id"):
                        ops.append(
                            UpdateOne({"id": item["id"]}, {"$set": item}, upsert=True)
                        )
                        count += 1

                        if len(ops) >= BATCH_SIZE:
                            collection.bulk_write(ops, ordered=False)
                            ops.clear()

                        if count % PROGRESS_EVERY == 0:
                            logger.info(f"Processed {count} items for MongoDB upsert.")
                except json.JSONDecodeError:
                    # 데이터 손상 시 스킵
                    continue

        if ops:
            collection.bulk_write(ops, ordered=False)

        logger.info(f"Finished loading data into MongoDB. Total processed items: {count}")
    except (PyMongoError, BulkWriteError) as e:
        logger.error(f"An error occurred during MongoDB bulk write: {e}")
    except FileNotFoundError:
        logger.error(f"Data file not found at {DATA_FILE_PATH}.")
    except Exception as e:
        logger.error(f"An error occurred during data loading: {e}")
    finally:
        if client:
            client.close()


if __name__ == "__main__":
    logger.info("Running scheduler as a standalone script.")
    load_arxiv_data_to_mongodb()
