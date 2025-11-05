from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import ConflictingIdError

# Settings를 초기화하여 .env 계층을 로드
from app.core.settings import settings

# 추가: 스케줄 작업으로 실행할 함수 연결
from app.scheduler.scheduler import parse_and_load, NT_FILE_PATH

# 추가: Auth 라우터 & DB 초기화
from app.api.routes.auth import router as auth_router
from app.db.mysql import init_db

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
JOB_ID = "dblp_loader_daily_4am"


# 추가: 실제 실행 함수 정의
def load_dblp_data_to_mongodb():
    parse_and_load(NT_FILE_PATH)


def _ensure_daily_job():
    """중복 등록을 피하면서 매일 04:00 작업을 보장."""
    if scheduler.get_job(JOB_ID):
        logger.info("Scheduler job already exists. Skipping add.")
        return
    try:
        scheduler.add_job(
            load_dblp_data_to_mongodb,
            trigger="cron",
            id=JOB_ID,
            hour=4,
            minute=0,
            coalesce=True,
            misfire_grace_time=3600,
            max_instances=1,
        )
        logger.info("Scheduled dblp loader at 04:00 Asia/Seoul.")
    except ConflictingIdError:
        logger.info("Scheduler job conflict. Using existing job.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # DB 테이블 준비
    init_db()
    _ensure_daily_job()
    if not scheduler.running:
        scheduler.start()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)

# Auth 라우터 등록
app.include_router(auth_router)


@app.get("/")
def root():
    # set은 JSON 직렬화 불가 -> dict로 반환
    return {"message": "Hello World!"}
