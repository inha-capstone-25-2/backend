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
import boto3
from botocore.exceptions import BotoCoreError, NoCredentialsError, ClientError
import requests  # 추가
import time  # 추가

from app.db.connection import get_mongo_collection

logger = logging.getLogger("uvicorn.error")

# 데이터 파일 경로
BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = BACKEND_ROOT / "data"
DATA_DIR = Path(os.getenv("DATA_DIR", str(DEFAULT_DATA_DIR)))
DATA_FILE_PATH = Path(os.getenv("ARXIV_FILE", str(DATA_DIR / "arxiv-metadata-oai-snapshot.json")))

BATCH_SIZE = int(os.getenv("ARXIV_BATCH_SIZE", "1000"))
PROGRESS_EVERY = int(os.getenv("ARXIV_PROGRESS_EVERY", "5000"))
MIN_FREE_GB = int(os.getenv("ARXIV_MIN_FREE_GB", "5"))

# 진행률 로그 설정(환경변수로 조절 가능)
CHUNK_SIZE = int(os.getenv("ARXIV_CHUNK_SIZE", str(1024 * 1024)))  # 1 MiB
PROGRESS_STEP_PERCENT = float(os.getenv("ARXIV_PROGRESS_STEP_PERCENT", "5"))  # 5%마다 로그
PROGRESS_MIN_LOG_SEC = float(os.getenv("ARXIV_PROGRESS_MIN_LOG_SEC", "2"))    # 최소 로그 간격(초)
PROGRESS_EVERY_MB = int(os.getenv("ARXIV_PROGRESS_EVERY_MB", "100"))          # Content-Length 없을 때 MB 주기

# S3 설정
S3_BUCKET = os.getenv("S3_BUCKET", "inha-capstone-02-arxiv")
S3_KEY = os.getenv("S3_KEY", "arxiv-metadata-oai-snapshot.json")

ARXIV_URL = os.getenv("ARXIV_URL")  # 프리사인 URL(선택)


def _has_enough_space(path: Path, need_gb: int) -> bool:
    total, used, free = shutil.disk_usage(path)
    free_gb = free // (1024**3)
    if free_gb < need_gb:
        logger.error(f"Not enough disk space at {path}: free={free_gb}GB need>={need_gb}GB")
        return False
    return True


def _fmt_bytes(n: float) -> str:  # 추가
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024.0:
            return f"{n:.1f}{unit}"
        n /= 1024.0
    return f"{n:.1f}PB"


def _fmt_eta(bytes_done: int, total: int, elapsed: float) -> str:  # 추가
    if bytes_done <= 0 or total <= 0:
        return "unknown"
    speed = bytes_done / max(elapsed, 1e-6)
    remain = max(total - bytes_done, 0)
    sec = int(remain / max(speed, 1e-6))
    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def download_arxiv_from_s3() -> bool:
    """
    S3에서 arxiv-metadata-oai-snapshot.json을 다운로드.
    - 버킷: S3_BUCKET
    - 키: S3_KEY
    - 목적지: DATA_FILE_PATH
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"[arxiv-job] S3 download target: {S3_BUCKET}/{S3_KEY} -> {DATA_FILE_PATH}")

    if DATA_FILE_PATH.exists():
        logger.info("[arxiv-job] local file exists; skip S3 download")
        return True
    if not _has_enough_space(DATA_DIR, MIN_FREE_GB):
        return False

    try:
        s3 = boto3.client("s3", region_name=os.getenv("AWS_DEFAULT_REGION"))
        tmp_path = DATA_FILE_PATH.with_suffix(".part")

        # 진행률 계산(총 크기 확인)
        total = None
        try:
            head = s3.head_object(Bucket=S3_BUCKET, Key=S3_KEY)
            total = int(head.get("ContentLength") or 0) or None
        except Exception:
            pass

        start_t = time.time()
        last_log = start_t
        downloaded = 0
        next_pct = PROGRESS_STEP_PERCENT if total else None

        def _cb(bytes_amount: int):
            nonlocal downloaded, last_log, next_pct
            downloaded += int(bytes_amount)
            now = time.time()
            if (now - last_log) < PROGRESS_MIN_LOG_SEC:
                return

            if total:
                pct = (downloaded / total) * 100.0
                if pct >= (next_pct or 1000):
                    last_log = now
                    speed = downloaded / max(now - start_t, 1e-3)
                    eta = _fmt_eta(downloaded, total, now - start_t)
                    logger.info(f"[arxiv-job] downloading {pct:.1f}% "
                                f"({_fmt_bytes(downloaded)}/{_fmt_bytes(total)}) "
                                f"at {_fmt_bytes(speed)}/s ETA {eta}")
                    while next_pct is not None and pct >= next_pct:
                        next_pct += PROGRESS_STEP_PERCENT
            else:
                # 총 크기 미상: MB 기준 주기 로그
                mb = downloaded / (1024 * 1024)
                if int(mb) % PROGRESS_EVERY_MB == 0:
                    last_log = now
                    speed = downloaded / max(now - start_t, 1e-3)
                    logger.info(f"[arxiv-job] downloading {_fmt_bytes(downloaded)} at {_fmt_bytes(speed)}/s")

        s3.download_file(S3_BUCKET, S3_KEY, str(tmp_path), Callback=_cb)
        tmp_path.replace(DATA_FILE_PATH)
        took = time.time() - start_t
        logger.info(f"[arxiv-job] S3 download complete in {took:.1f}s size={_fmt_bytes(DATA_FILE_PATH.stat().st_size)}")
        return True
    except (NoCredentialsError, ClientError, BotoCoreError) as e:
        logger.error(f"[arxiv-job] S3 download failed: {e}")
        return False
    except Exception as e:
        logger.error(f"[arxiv-job] unexpected S3 error: {e}")
        return False


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


def download_arxiv_from_url() -> bool:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if DATA_FILE_PATH.exists():
        logger.info("[arxiv-job] local file exists; skip URL download")
        return True
    if not _has_enough_space(DATA_DIR, MIN_FREE_GB):
        return False
    if not ARXIV_URL:
        logger.error("[arxiv-job] ARXIV_URL not set")
        return False
    logger.info(f"[arxiv-job] URL download -> {DATA_FILE_PATH}")
    tmp_path = DATA_FILE_PATH.with_suffix(".part")
    try:
        start_t = time.time()
        last_log = start_t
        downloaded = 0
        with requests.get(ARXIV_URL, stream=True, timeout=600) as r:
            r.raise_for_status()
            total = int(r.headers.get("Content-Length") or 0)
            next_pct = PROGRESS_STEP_PERCENT if total > 0 else None

            with open(tmp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded += len(chunk)

                    now = time.time()
                    # 로그 최소 간격 보장
                    if (now - last_log) < PROGRESS_MIN_LOG_SEC:
                        continue

                    if total > 0:
                        pct = (downloaded / total) * 100.0
                        if pct >= (next_pct or 1000):
                            speed = downloaded / max(now - start_t, 1e-3)
                            eta = _fmt_eta(downloaded, total, now - start_t)
                            logger.info(f"[arxiv-job] downloading {pct:.1f}% "
                                        f"({_fmt_bytes(downloaded)}/{_fmt_bytes(total)}) "
                                        f"at {_fmt_bytes(speed)}/s ETA {eta}")
                            last_log = now
                            while next_pct is not None and pct >= next_pct:
                                next_pct += PROGRESS_STEP_PERCENT
                    else:
                        # Content-Length 없으면 MB 기준 주기 로그
                        mb = downloaded / (1024 * 1024)
                        if int(mb) % PROGRESS_EVERY_MB == 0 and mb >= 1:
                            speed = downloaded / max(now - start_t, 1e-3)
                            logger.info(f"[arxiv-job] downloading {_fmt_bytes(downloaded)} at {_fmt_bytes(speed)}/s")
                            last_log = now

        tmp_path.replace(DATA_FILE_PATH)
        took = time.time() - start_t
        logger.info(f"[arxiv-job] URL download complete in {took:.1f}s size={_fmt_bytes(DATA_FILE_PATH.stat().st_size)}")
        return True
    except Exception as e:
        logger.error(f"[arxiv-job] URL download failed: {e}")
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass
        return False


def load_arxiv_data_to_mongodb() -> bool:
    """
    내부 스케줄러/API가 호출하는 Mongo 적재 작업.
    - 파일이 없으면 S3에서 내려받아 사용
    """
    logger.info("[arxiv-job] start")
    if not DATA_FILE_PATH.exists():
        # 1) 프리사인 URL 우선
        if ARXIV_URL and download_arxiv_from_url():
            pass
        # 2) URL 실패 시 S3 시도(자격 없으면 자동 실패)
        elif download_arxiv_from_s3():
            pass
        else:
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
