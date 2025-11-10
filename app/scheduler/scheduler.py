from __future__ import annotations
import json
import logging
import os
from pathlib import Path
from pymongo import UpdateOne
from pymongo.errors import PyMongoError, BulkWriteError
import shutil
from zipfile import ZipFile  # 추가
import sys  # 추가
import subprocess

from app.db.connection import get_mongo_collection

logger = logging.getLogger("uvicorn.error")

# 데이터 파일 경로
BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = BACKEND_ROOT / "data"
DATA_DIR = Path(os.getenv("DATA_DIR", str(DEFAULT_DATA_DIR)))
DATA_FILE_PATH = Path(os.getenv("ARXIV_FILE", str(DATA_DIR / "arxiv-metadata-oai-snapshot.json")))

BATCH_SIZE = int(os.getenv("ARXIV_BATCH_SIZE", "1000"))
PROGRESS_EVERY = int(os.getenv("ARXIV_PROGRESS_EVERY", "5000"))
MIN_FREE_GB = int(os.getenv("ARXIV_MIN_FREE_GB", "10"))

DATASET = "Cornell-University/arxiv"
FILENAME = "arxiv-metadata-oai-snapshot.json"


def _has_enough_space(path: Path, need_gb: int) -> bool:
    total, used, free = shutil.disk_usage(path)
    free_gb = free // (1024**3)
    if free_gb < need_gb:
        logger.error(f"Not enough disk space at {path}: free={free_gb}GB need>={need_gb}GB")
        return False
    return True


def download_arxiv_snapshot() -> bool:
    """
    arxiv-metadata-oai-snapshot.json 단일 파일만 Kaggle에서 다운로드.
    - Kaggle CLI를 서브프로세스로 실행하여 sys.exit가 서버 프로세스를 종료하지 않도록 격리
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"[arxiv-job] DATA_DIR={DATA_DIR} FILE={DATA_FILE_PATH}")
    if DATA_FILE_PATH.exists():
        logger.info("[arxiv-job] file already present; skip download")
        return True
    if not _has_enough_space(DATA_DIR, MIN_FREE_GB):
        return False

    zip_path = DATA_DIR / f"{FILENAME}.zip"
    try:
        # Kaggle CLI 실행
        env = os.environ.copy()
        env.setdefault("KAGGLE_CONFIG_DIR", "/root/.kaggle")
        cmd = [
            "kaggle", "datasets", "download",
            "-d", DATASET,
            "-f", FILENAME,
            "-p", str(DATA_DIR),
            "--quiet",
        ]
        logger.info(f"[arxiv-job] running CLI: {' '.join(cmd)}")
        res = subprocess.run(
            cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3600
        )
        if res.returncode != 0:
            logger.error(f"[arxiv-job] kaggle CLI failed (rc={res.returncode}) stderr={res.stderr.strip()}")
            return False
        if res.stdout.strip():
            logger.info(f"[arxiv-job] kaggle CLI stdout: {res.stdout.strip().splitlines()[-1]}")

        # unzip 및 검증
        if zip_path.exists():
            logger.info("[arxiv-job] extracting zip")
            with ZipFile(zip_path) as zf:
                zf.extract(FILENAME, path=str(DATA_DIR))
            try:
                zip_path.unlink()
            except OSError:
                pass

        if not DATA_FILE_PATH.exists():
            logger.error("[arxiv-job] downloaded but JSON not found")
            return False

        logger.info("[arxiv-job] download complete")
        return True

    except FileNotFoundError:
        logger.error("[arxiv-job] kaggle CLI not found. Ensure 'kaggle' package is installed.")
        return False
    except subprocess.TimeoutExpired:
        logger.error("[arxiv-job] kaggle CLI timed out")
        return False
    except Exception as e:
        logger.error(f"[arxiv-job] kaggle download failed: {e}")
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
