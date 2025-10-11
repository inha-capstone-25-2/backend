from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import ConflictingIdError
from .scheduler.scheduler import load_arxiv_data_to_mongodb  # 변경: 최신 함수 사용

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
JOB_ID = "arxiv_loader_daily_4am"


def _ensure_daily_job():
    """중복 등록을 피하면서 매일 04:00 작업을 보장."""
    if scheduler.get_job(JOB_ID):
        logger.info("Scheduler job already exists. Skipping add.")
        return
    try:
        scheduler.add_job(
            load_arxiv_data_to_mongodb,
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
    _ensure_daily_job()
    if not scheduler.running:
        scheduler.start()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)


@app.get("/")
def root():
    return {"Hello World!"}
