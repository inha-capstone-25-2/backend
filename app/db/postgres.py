from __future__ import annotations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from app.core.settings import settings

Base = declarative_base()

_engine = None
_SessionLocal = None

def _postgres_url() -> str:
    host = settings.db_host
    port = settings.db_port
    user = settings.db_user
    password = settings.db_password
    db = settings.db_name
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(_postgres_url(), pool_pre_ping=True, future=True)
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
    Base.metadata.create_all(bind=get_engine())