"""PostgreSQL 데이터베이스 연결 설정.

SQLAlchemy를 사용하여 PostgreSQL 연결을 관리합니다.
"""

from __future__ import annotations
import logging
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from app.core.settings import settings

Base = declarative_base()

_engine = None
_SessionLocal = None

logger = logging.getLogger(__name__)


def _postgres_url() -> str:
    """PostgreSQL 연결 URL을 생성한다.

    Returns:
        PostgreSQL 연결 URL 문자열.
    """
    host = settings.db_host
    port = settings.db_port
    user = quote_plus(settings.db_user or "")
    password = quote_plus(settings.db_password or "")
    db = settings.db_name
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


def get_engine():
    """SQLAlchemy 엔진 싱글톤을 반환한다.

    Returns:
        SQLAlchemy Engine 인스턴스.
    """
    global _engine
    if _engine is None:
        url = _postgres_url()
        logger.info(
            f"Initializing Postgres engine host={settings.db_host} port={settings.db_port} "
            f"user={settings.db_user} db={settings.db_name}"
        )
        _engine = create_engine(url, pool_pre_ping=True, future=True)
    return _engine


def _get_sessionmaker():
    """SQLAlchemy SessionLocal 싱글톤을 반환한다.

    Returns:
        SessionLocal 클래스.
    """
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(), autocommit=False, autoflush=False, future=True
        )
    return _SessionLocal


def get_db() -> Session:
    """FastAPI Dependency Injection용 DB 세션을 반환한다.

    Yields:
        SQLAlchemy Session 인스턴스.
    """
    db = _get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """데이터베이스 테이블을 초기화한다.

    Base에 등록된 모든 모델의 테이블을 생성합니다.
    """
    Base.metadata.create_all(bind=get_engine())


def close_postgres() -> None:
    """PostgreSQL 연결을 종료한다.

    애플리케이션 종료 시 호출됩니다.
    """
    global _engine, _SessionLocal
    
    if _engine:
        _engine.dispose()
        _engine = None
        logger.info("PostgreSQL engine disposed")
    
    _SessionLocal = None
