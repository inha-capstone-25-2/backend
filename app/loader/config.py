from pathlib import Path
import os

# 데이터 파일 경로
BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = BACKEND_ROOT / "data"
DATA_DIR = Path(os.getenv("DATA_DIR", str(DEFAULT_DATA_DIR)))
DATA_FILE_PATH = Path(os.getenv("ARXIV_FILE", str(DATA_DIR / "arxiv-metadata-oai-snapshot.json")))

# 배치 및 진행률 설정
BATCH_SIZE = int(os.getenv("ARXIV_BATCH_SIZE", "1000"))
PROGRESS_EVERY = int(os.getenv("ARXIV_PROGRESS_EVERY", "5000"))
MIN_FREE_GB = int(os.getenv("ARXIV_MIN_FREE_GB", "5"))

# S3 설정
S3_BUCKET = os.getenv("S3_BUCKET", "inha-capstone-02-arxiv")
S3_KEY = os.getenv("S3_KEY", "arxiv-metadata-oai-snapshot.json")
ARXIV_URL = os.getenv("ARXIV_URL")