"""arXiv 데이터 로더 모듈.

arXiv 데이터를 다운로드하고 MongoDB에 적재하는 메인 로직을 담당합니다.
"""

from __future__ import annotations
import logging
from app.loader.arxiv_download import ensure_arxiv_file
from app.loader.arxiv_mongo import ingest_arxiv_to_mongo, copy_prod_to_local_mongo
from app.core.settings import settings

logger = logging.getLogger(__name__)


def load_arxiv_data_to_mongodb() -> bool:
    """
    arXiv 데이터 로드 메인 함수.
    - local: prod MongoDB에서 복제
    - dev/prod: S3/URL 다운로드 후 MongoDB 적재
    """
    if settings.app_env == "local":
        logger.info("[arxiv-job] local env: copying from prod MongoDB")
        return copy_prod_to_local_mongo()
    else:
        logger.info(f"[arxiv-job] {settings.app_env} env: downloading and ingesting")
        if not ensure_arxiv_file():
            logger.error("[arxiv-job] file preparation failed")
            return False
        return ingest_arxiv_to_mongo()
