import logging
from typing import Generator
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError
from app.core.settings import settings

logger = logging.getLogger(__name__)

# 글로벌 MongoDB 클라이언트 인스턴스
_mongo_client: MongoClient | None = None
_mongo_db: Database | None = None


def init_mongo() -> None:
    """
    애플리케이션 시작 시 MongoDB 클라이언트 초기화.
    FastAPI lifespan에서 호출됨.
    """
    global _mongo_client, _mongo_db
    
    host = settings.mongo_host
    port = settings.mongo_port
    user = settings.mongo_user
    password = settings.mongo_password
    auth_source = settings.mongo_auth_source
    db_name = settings.mongo_db

    if not host:
        logger.error("MONGO_HOST is not set. MongoDB will not be initialized.")
        return

    if user and password:
        mongo_uri = f"mongodb://{user}:{password}@{host}:{port}/?authSource={auth_source}"
    else:
        mongo_uri = f"mongodb://{host}:{port}/"

    try:
        _mongo_client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=5000,
            maxPoolSize=100,  # 연결 풀 크기 명시
        )
        # 연결 테스트
        _mongo_client.admin.command("ping")
        _mongo_db = _mongo_client[db_name]
        logger.info(
            f"MongoDB initialized: host={host}:{port} db={db_name} "
            f"user={user or 'none'}"
        )
    except PyMongoError as e:
        logger.error(f"MongoDB initialization failed: {e}")
        _mongo_client = None
        _mongo_db = None


def close_mongo() -> None:
    """
    애플리케이션 종료 시 MongoDB 클라이언트 종료.
    FastAPI lifespan에서 호출됨.
    """
    global _mongo_client, _mongo_db
    
    if _mongo_client:
        try:
            _mongo_client.close()
            logger.info("MongoDB connection closed")
        except Exception as e:
            logger.error(f"Error closing MongoDB connection: {e}")
        finally:
            _mongo_client = None
            _mongo_db = None


def get_mongo_db() -> Generator[Database, None, None]:
    """
    FastAPI Dependency Injection용 MongoDB 데이터베이스 제공.
    PostgreSQL의 get_db()와 동일한 패턴.
    
    Usage:
        @router.get("/endpoint")
        def endpoint(db: Database = Depends(get_mongo_db)):
            collection = db["collection_name"]
            ...
    """
    if _mongo_db is None:
        raise RuntimeError(
            "MongoDB is not initialized. Call init_mongo() first."
        )
    
    # PyMongo는 자체적으로 연결 풀을 관리하므로
    # 단순히 db 인스턴스를 yield하면 됨
    yield _mongo_db


def get_mongo_client_direct() -> MongoClient:
    """
    배치 작업 등 Dependency Injection을 사용할 수 없는 곳에서
    MongoDB 클라이언트에 직접 접근하기 위한 헬퍼 함수.
    
    Warning: 이 함수는 FastAPI 라우터가 아닌 곳에서만 사용하세요.
    라우터에서는 get_mongo_db() Dependency를 사용하세요.
    """
    if _mongo_client is None:
        raise RuntimeError(
            "MongoDB is not initialized. Call init_mongo() first."
        )
    return _mongo_client


def get_prod_mongo_client() -> MongoClient:
    """
    Production MongoDB 클라이언트를 생성하여 반환.
    로컬 환경에서 데이터 복제 시에만 사용.
    
    Warning: 
    - 이 함수는 새로운 연결을 생성하므로 사용 후 반드시 close() 해야 함.
    - 글로벌 클라이언트가 아닌 임시 연결임.
    
    Raises:
        RuntimeError: PROD_MONGO_HOST가 설정되지 않은 경우
    """
    host = settings.prod_mongo_host
    port = settings.prod_mongo_port
    user = settings.prod_mongo_user
    password = settings.prod_mongo_password
    auth_source = settings.prod_mongo_auth_source

    if not host:
        raise RuntimeError(
            "PROD_MONGO_HOST is not set. Cannot connect to production MongoDB."
        )

    if user and password:
        mongo_uri = f"mongodb://{user}:{password}@{host}:{port}/?authSource={auth_source}"
    else:
        mongo_uri = f"mongodb://{host}:{port}/"

    try:
        client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=10000,  # prod는 외부 네트워크이므로 타임아웃 길게
            maxPoolSize=10,  # 임시 연결이므로 작은 풀 사용
        )
        # 연결 테스트
        client.admin.command("ping")
        logger.info(
            f"Production MongoDB client created: host={host}:{port} "
            f"user={user or 'none'}"
        )
        return client
    except PyMongoError as e:
        logger.error(f"Failed to connect to production MongoDB: {e}")
        raise
