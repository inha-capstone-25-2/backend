"""작업 API 라우터 모듈.

arXiv 데이터 로딩 등 백그라운드 작업 엔드포인트를 정의합니다.
"""

from fastapi import APIRouter, BackgroundTasks
from app.loader.arxiv_loader import load_arxiv_data_to_mongodb
import logging

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _run():
    log = logging.getLogger("uvicorn.error")
    log.info("[arxiv-job][manual] accepted background start")
    ok = load_arxiv_data_to_mongodb()
    if ok:
        log.info("[arxiv-job][manual] success")
    else:
        log.error("[arxiv-job][manual] failed")


@router.post("/arxiv/run", status_code=202)
def run_arxiv(background: BackgroundTasks):
    background.add_task(_run)
    return {"accepted": True}
