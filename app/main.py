from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import ConflictingIdError
import os

# 3. 앱 시작 시 로깅 설정 적용
from app.core.logging_config import setup_logging  # 추가
setup_logging()  # 가장 먼저 호출

# Settings를 초기화하여 .env 계층을 로드
from app.core.settings import settings
from app.core.exceptions import (
    AppException,
    DatabaseException,
    MongoDBException,
    PostgreSQLException,
    BusinessLogicException,
    ResourceNotFoundException,
    ValidationException,
)

# 추가: Auth 라우터 & DB 초기화
from app.api.routes.auth import router as auth_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.papers import router as papers_router
from app.api.routes.categories import router as categories_router
from app.api.routes.user_interests import router as user_interests_router
from app.api.routes.bookmarks import router as bookmarks_router
from app.api.routes.activities import router as activities_router
from app.api.routes.recommendations import router as recommendations_router
from app.db.postgres import init_db, get_db
from app.loader.arxiv_loader import load_arxiv_data_to_mongodb
from app.seed.categories_seed import seed_categories  # 추가

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
    # Startup
    try:
        # PostgreSQL 테이블 준비
        init_db()
    except Exception as e:
        logger.error(f"init_db failed: {e}")

    # MongoDB 연결 초기화
    try:
        from app.db.mongodb import init_mongo
        init_mongo()
    except Exception as e:
        logger.error(f"init_mongo failed: {e}")

    _ensure_daily_job()
    if not scheduler.running:
        scheduler.start()
    
    yield
    
    # Shutdown
    if scheduler.running:
        scheduler.shutdown(wait=False)
    
    # MongoDB 연결 종료
    try:
        from app.db.mongodb import close_mongo
        close_mongo()
    except Exception as e:
        logger.error(f"close_mongo failed: {e}")


app = FastAPI(lifespan=lifespan)


# Exception handlers
@app.exception_handler(DatabaseException)
async def database_exception_handler(request: Request, exc: DatabaseException):
    """데이터베이스 관련 예외 처리"""
    logger.error(f"Database error at {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Database operation failed",
            "type": "database_error",
            "path": str(request.url.path),
        }
    )


@app.exception_handler(ResourceNotFoundException)
async def resource_not_found_handler(request: Request, exc: ResourceNotFoundException):
    """리소스를 찾을 수 없음 예외 처리"""
    logger.warning(f"Resource not found at {request.url.path}: {exc}")
    return JSONResponse(
        status_code=404,
        content={
            "detail": str(exc),
            "type": "resource_not_found",
            "path": str(request.url.path),
        }
    )


@app.exception_handler(ValidationException)
async def validation_exception_handler(request: Request, exc: ValidationException):
    """입력값 검증 실패 예외 처리"""
    logger.warning(f"Validation error at {request.url.path}: {exc}")
    return JSONResponse(
        status_code=400,
        content={
            "detail": str(exc),
            "type": "validation_error",
            "path": str(request.url.path),
        }
    )


@app.exception_handler(BusinessLogicException)
async def business_logic_exception_handler(request: Request, exc: BusinessLogicException):
    """비즈니스 로직 예외 처리"""
    logger.warning(f"Business logic error at {request.url.path}: {exc}")
    return JSONResponse(
        status_code=400,
        content={
            "detail": str(exc),
            "type": "business_logic_error",
            "path": str(request.url.path),
        }
    )


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """일반 애플리케이션 예외 처리"""
    logger.warning(f"Application error at {request.url.path}: {exc}")
    return JSONResponse(
        status_code=400,
        content={
            "detail": str(exc),
            "type": "application_error",
            "path": str(request.url.path),
        }
    )


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

# Auth 라우터 등록
app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(papers_router)
app.include_router(categories_router)
app.include_router(user_interests_router)
app.include_router(bookmarks_router)
app.include_router(activities_router)
app.include_router(recommendations_router)


@app.get("/")
def root():
    # set은 JSON 직렬화 불가 -> dict로 반환
    return {"message": "Hello World!"}
