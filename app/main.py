from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import ConflictingIdError
import os

# 앱 시작 시 로깅 설정 적용
from app.core.logging_config import setup_logging

setup_logging()

# Settings
from app.core.settings import settings
from app.core.exceptions import AppException

# 라우터
from app.api.routes.auth import router as auth_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.papers import router as papers_router
from app.api.routes.categories import router as categories_router
from app.api.routes.user_interests import router as user_interests_router
from app.api.routes.bookmarks import router as bookmarks_router
from app.api.routes.activities import router as activities_router
from app.api.routes.recommendations import router as recommendations_router
from app.api.routes.recommendation_events import router as recommendation_events_router
from app.db.postgres import init_db
from app.loader.arxiv_loader import load_arxiv_data_to_mongodb

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
            _run_scheduled_arxiv_job,
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
    # Startup
    try:
        init_db()
    except Exception as e:
        logger.error(f"init_db failed: {e}")

    try:
        from app.db.mongodb import init_mongo

        init_mongo()
    except Exception as e:
        logger.error(f"init_mongo failed: {e}")

    try:
        from app.db.elasticsearch import init_elasticsearch

        init_elasticsearch()
    except Exception as e:
        logger.error(f"init_elasticsearch failed: {e}")

    _ensure_daily_job()
    if not scheduler.running:
        scheduler.start()

    yield

    # Shutdown
    if scheduler.running:
        scheduler.shutdown(wait=False)

    try:
        from app.db.mongodb import close_mongo

        close_mongo()
    except Exception as e:
        logger.error(f"close_mongo failed: {e}")

    try:
        from app.db.postgres import close_postgres

        close_postgres()
    except Exception as e:
        logger.error(f"close_postgres failed: {e}")

    try:
        from app.db.elasticsearch import close_elasticsearch

        close_elasticsearch()
    except Exception as e:
        logger.error(f"close_elasticsearch failed: {e}")

    try:
        from app.db.ssh_tunnel import ssh_tunnel_manager

        ssh_tunnel_manager.close_all_tunnels()
    except Exception as e:
        logger.error(f"close_all_tunnels failed: {e}")


app = FastAPI(lifespan=lifespan)


# Exception handlers - 중앙화된 유틸리티 사용
from app.core.exception_handlers import create_error_response, get_exception_config


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """모든 커스텀 예외 처리 (계층 구조 활용)"""
    status_code, error_type, log_level = get_exception_config(exc)
    return create_error_response(request, exc, status_code, error_type, log_level)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """처리되지 않은 예외 처리"""
    logger.error(f"Unhandled exception at {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "error_type": "internal_server_error",
            "path": str(request.url.path),
        },
    )


# CORS
cors_env = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001")
allowed_origins = [o.strip() for o in cors_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Authorization"],
)

# 라우터 등록
app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(papers_router)
app.include_router(categories_router)
app.include_router(user_interests_router)
app.include_router(bookmarks_router)
app.include_router(activities_router)
app.include_router(recommendations_router)
app.include_router(recommendation_events_router)


@app.get("/")
def root():
    return {"message": "Hello World!"}
