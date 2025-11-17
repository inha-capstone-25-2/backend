from __future__ import annotations
import logging
from app.loader.arxiv_download import ensure_arxiv_file
from app.loader.arxiv_mongo import ingest_arxiv_to_mongo, copy_prod_to_local_mongo
from app.core.settings import settings

logger = logging.getLogger("uvicorn.error")

def load_arxiv_data_to_mongodb() -> bool:
    """
    arXiv 데이터 로드 메인 함수.
    - 로컬: prod MongoDB에서 복제
    - prod: S3/URL 다운로드 후 MongoDB 적재
    """
    if settings.app_env == "local":
        logger.info("[arxiv-job] local env: copying from prod MongoDB")
        return copy_prod_to_local_mongo()
    else:
        logger.info("[arxiv-job] prod env: downloading and ingesting")
        if not ensure_arxiv_file():
            logger.error("[arxiv-job] file preparation failed")
            return False
        return ingest_arxiv_to_mongo()
