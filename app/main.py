from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import ConflictingIdError

# Settings를 초기화하여 .env 계층을 로드
from app.core.settings import settings

# 추가: Auth 라우터 & DB 초기화
from app.api.routes.auth import router as auth_router
from app.api.routes.jobs import router as jobs_router  # 추가
from app.db.postgres import init_db
from app.scheduler.scheduler import load_arxiv_data_to_mongodb  # 추가

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
JOB_ID = "arxiv_loader_daily_4am"


def _run_scheduled_arxiv_job():
    log = logging.getLogger("uvicorn.error")
    log.info("[arxiv-job][scheduled] triggered")
    ok = load_arxiv_data_to_mongodb()
    if ok:
        log.info("[arxiv-job][scheduled] success")
    else:
        log.error("[arxiv-job][scheduled] failed")

def _ensure_daily_job():
    """중복 등록을 피하면서 매일 04:00 작업을 보장."""
    if scheduler.get_job(JOB_ID):
        logger.info("Scheduler job already exists. Skipping add.")
        return
    try:
        scheduler.add_job(
            _run_scheduled_arxiv_job,   # 래퍼로 교체
            trigger="cron",
            id=JOB_ID,
            hour=4,
            minute=0,
            coalesce=True,
            misfire_grace_time=3600,
            max_instances=1,
        )
        logger.info("Scheduled arxiv loader at 04:00 Asia/Seoul.")
    except ConflictingIdError:
        logger.info("Scheduler job conflict. Using existing job.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # DB 테이블 준비
        init_db()
    except Exception as e:
        logger.error(f"init_db failed: {e}")
    _ensure_daily_job()
    if not scheduler.running:
        scheduler.start()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)

# Auth 라우터 등록
app.include_router(auth_router)
app.include_router(jobs_router)  # 추가


@app.get("/")
def root():
    # set은 JSON 직렬화 불가 -> dict로 반환
    return {"message": "Hello World!"}
