from __future__ import annotations
import logging
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from app.core.settings import settings
from app.db.ssh_tunnel import ssh_tunnel_manager

Base = declarative_base()

_engine = None
_SessionLocal = None

logger = logging.getLogger(__name__)


def _postgres_url() -> str:
    host = settings.db_host
    port = settings.db_port
    
    # SSH 터널링이 활성화되어 있고 터널이 생성된 경우 로컬 포트 사용
    # (get_engine에서 터널 생성 후 호출됨)
    if settings.db_ssh_host:
        tunnel = ssh_tunnel_manager.get_tunnel("postgres")
        if tunnel:
            host = "localhost"
            port = settings.db_local_bind_port

    user = quote_plus(settings.db_user or "")
    password = quote_plus(settings.db_password or "")
    db = settings.db_name
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


def get_engine():
    global _engine
    if _engine is None:
        # SSH 터널링 설정 확인 및 적용
        if settings.db_ssh_host:
            try:
                ssh_tunnel_manager.create_tunnel(
                    name="postgres",
                    ssh_host=settings.db_ssh_host,
                    ssh_port=settings.db_ssh_port,
                    ssh_user=settings.db_ssh_user,
                    ssh_pkey=settings.db_ssh_pem_key_path,
                    remote_bind_address=("127.0.0.1", settings.db_port),
                    local_bind_port=settings.db_local_bind_port,
                )
                logger.info(f"PostgreSQL SSH tunnel established on localhost:{settings.db_local_bind_port}")
            except Exception as e:
                logger.error(f"Failed to establish SSH tunnel for PostgreSQL: {e}")
                raise

        url = _postgres_url()
        logger.info(
            f"Initializing Postgres engine host={settings.db_host} port={settings.db_port} "
            f"user={settings.db_user} db={settings.db_name}"
        )
        _engine = create_engine(url, pool_pre_ping=True, future=True)
    return _engine


def _get_sessionmaker():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(), autocommit=False, autoflush=False, future=True
        )
    return _SessionLocal


def get_db() -> Session:
    db = _get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=get_engine())


def close_postgres():
    """
    PostgreSQL 연결 및 SSH 터널 종료
    """
    global _engine, _SessionLocal
    
    if _engine:
        _engine.dispose()
        _engine = None
        logger.info("PostgreSQL engine disposed")
    
    _SessionLocal = None

    # SSH 터널 종료
    if settings.db_ssh_host:
        ssh_tunnel_manager.close_tunnel("postgres")
