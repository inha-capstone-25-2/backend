from __future__ import annotations
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

Base = declarative_base()

_engine = None
_SessionLocal = None

def _mysql_url() -> str:
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    db = os.getenv("DB_NAME", "app")
    return f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{db}?charset=utf8mb4"

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(_mysql_url(), pool_pre_ping=True, future=True)
    return _engine

def _get_sessionmaker():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False, future=True)
    return _SessionLocal

def get_db() -> Session:
    db = _get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()

def init_db():
    # 테이블 생성
    Base.metadata.create_all(bind=get_engine())