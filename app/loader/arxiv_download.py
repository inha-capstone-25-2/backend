from __future__ import annotations
import json
import logging
import os
from pathlib import Path
import shutil
import boto3
from botocore.exceptions import BotoCoreError, NoCredentialsError, ClientError
import requests

from app.core.settings import settings
from app.loader.config import DATA_DIR, DATA_FILE_PATH, MIN_FREE_GB, S3_BUCKET, S3_KEY, ARXIV_URL
from app.loader.utils import _fmt_bytes, _fmt_eta, get_current_time  # 추가

logger = logging.getLogger("uvicorn.error")

# 데이터 파일 경로
BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = BACKEND_ROOT / "data"
DATA_DIR = Path(os.getenv("DATA_DIR", str(DEFAULT_DATA_DIR)))
DATA_FILE_PATH = Path(os.getenv("ARXIV_FILE", str(DATA_DIR / "arxiv-metadata-oai-snapshot.json")))

BATCH_SIZE = int(os.getenv("ARXIV_BATCH_SIZE", "1000"))
PROGRESS_EVERY = int(os.getenv("ARXIV_PROGRESS_EVERY", "5000"))
MIN_FREE_GB = int(os.getenv("ARXIV_MIN_FREE_GB", "5"))

# S3 설정
S3_BUCKET = os.getenv("S3_BUCKET", "inha-capstone-02-arxiv")
S3_KEY = os.getenv("S3_KEY", "arxiv-metadata-oai-snapshot.json")
ARXIV_URL = os.getenv("ARXIV_URL")

def _has_enough_space(path: Path, need_gb: int) -> bool:
    total, used, free = shutil.disk_usage(path)
    free_gb = free // (1024**3)
    if free_gb < need_gb:
        logger.error(f"Not enough disk space at {path}: free={free_gb}GB need>={need_gb}GB")
        return False
    return True

def download_arxiv_from_s3() -> bool:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"[arxiv-job] S3 download target: {S3_BUCKET}/{S3_KEY} -> {DATA_FILE_PATH}")

    if DATA_FILE_PATH.exists():
        logger.info("[arxiv-job] local file exists; skip S3 download")
        return True
    if not _has_enough_space(DATA_DIR, MIN_FREE_GB):
        return False
    if not _has_aws_credentials():
        logger.warning("[arxiv-job] no AWS credentials; skip S3")
        return False

    try:
        s3 = boto3.client("s3", region_name=os.getenv("AWS_DEFAULT_REGION"))
        tmp_path = DATA_FILE_PATH.with_suffix(".part")

        total = None
        try:
            head = s3.head_object(Bucket=S3_BUCKET, Key=S3_KEY)
            total = int(head.get("ContentLength") or 0) or None
        except Exception:
            pass

        start_t = get_current_time()
        last_log = start_t
        downloaded = 0
        next_pct = 5.0 if total else None

        def _cb(bytes_amount: int):
            nonlocal downloaded, last_log, next_pct
            downloaded += int(bytes_amount)
            now = get_current_time()
            if (now - last_log) < 2:
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
                        next_pct += 5.0

        s3.download_file(S3_BUCKET, S3_KEY, str(tmp_path), Callback=_cb)
        tmp_path.replace(DATA_FILE_PATH)
        took = get_current_time() - start_t
        logger.info(f"[arxiv-job] S3 download complete in {took:.1f}s size={_fmt_bytes(DATA_FILE_PATH.stat().st_size)}")
        return True
    except (NoCredentialsError, ClientError, BotoCoreError) as e:
        logger.error(f"[arxiv-job] S3 download failed: {e}")
        return False
    except Exception as e:
        logger.error(f"[arxiv-job] unexpected S3 error: {e}")
        return False

def download_arxiv_from_presigned_url() -> bool:
    if not ARXIV_URL:
        logger.error("[arxiv-job] ARXIV_URL not set")
        return False

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if DATA_FILE_PATH.exists():
        logger.info("[arxiv-job] local file exists; skip URL download")
        return True
    if not _has_enough_space(DATA_DIR, MIN_FREE_GB):
        return False

    tmp_path = DATA_FILE_PATH.with_suffix(".part")
    try:
        with requests.get(ARXIV_URL, stream=True, timeout=60) as r:
            r.raise_for_status()
            total = int(r.headers.get("Content-Length") or 0)
            start_t = get_current_time()
            last_log = start_t
            downloaded = 0
            next_pct = 5.0 if total else None
            with open(tmp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded += len(chunk)
                    now = get_current_time()
                    if total and (now - last_log) >= 2:
                        pct = (downloaded / total) * 100.0
                        if pct >= (next_pct or 1000):
                            last_log = now
                            speed = downloaded / max(now - start_t, 1e-3)
                            eta = _fmt_eta(downloaded, total, now - start_t)
                            logger.info(f"[arxiv-job] url downloading {pct:.1f}% "
                                        f"({_fmt_bytes(downloaded)}/{_fmt_bytes(total)}) "
                                        f"at {_fmt_bytes(speed)}/s ETA {eta}")
                            while next_pct is not None and pct >= next_pct:
                                next_pct += 5.0
        tmp_path.replace(DATA_FILE_PATH)
        took = get_current_time() - start_t
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

def ensure_arxiv_file() -> bool:
    if DATA_FILE_PATH.exists():
        return True
    if download_arxiv_from_s3():
        return True
    if download_arxiv_from_presigned_url():
        return True
    return False