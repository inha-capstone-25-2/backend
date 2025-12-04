import logging
from typing import Generator, Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError
from app.core.settings import settings


logger = logging.getLogger(__name__)


class MongoDBManager:
    """
    MongoDB 연결을 관리하는 싱글톤 스타일 클래스.
    """

    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None

    def connect(self, skip_indexes: bool = False) -> None:
        """MongoDB 연결 초기화
        
        Args:
            skip_indexes: True이면 인덱스 생성을 건너뜀 (Celery worker용)
        """
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
            mongo_uri = (
                f"mongodb://{user}:{password}@{host}:{port}/?authSource={auth_source}"
            )
        else:
            mongo_uri = f"mongodb://{host}:{port}/"

        try:
            self.client = MongoClient(
                mongo_uri,
                serverSelectionTimeoutMS=5000,
                maxPoolSize=100,
            )
            # 연결 테스트
            self.client.admin.command("ping")
            self.db = self.client[db_name]
            logger.info(
                f"MongoDB initialized: host={host}:{port} db={db_name} "
                f"user={user or 'none'}"
            )

            if not skip_indexes:
                self._create_indexes()

        except PyMongoError as e:
            logger.error(f"MongoDB initialization failed: {e}")
            self.client = None
            self.db = None
            raise

    def _create_indexes(self) -> None:
        """필요한 인덱스 생성 (app/db/indexes.py 위임)"""
        if self.db is None:
            return

        from app.db.indexes import ensure_indexes
        
        # papers 컬렉션 포함 모든 인덱스 생성
        ensure_indexes(self.db, skip_papers=False)


    def close(self) -> None:
        """MongoDB 연결 종료"""
        if self.client:
            try:
                self.client.close()
                logger.info("MongoDB connection closed")
            except Exception as e:
                logger.error(f"Error closing MongoDB connection: {e}")
            finally:
                self.client = None
                self.db = None

    def get_db(self) -> Database:
        """Database 인스턴스 반환"""
        if self.db is None:
            raise RuntimeError("MongoDB is not initialized. Call connect() first.")
        return self.db

    def get_client(self) -> MongoClient:
        """MongoClient 인스턴스 반환"""
        if self.client is None:
            raise RuntimeError("MongoDB is not initialized. Call connect() first.")
        return self.client


# 전역 인스턴스 생성
db_manager = MongoDBManager()


def init_mongo() -> None:
    """애플리케이션 시작 시 호출"""
    db_manager.connect()


def close_mongo() -> None:
    """애플리케이션 종료 시 호출"""
    db_manager.close()


def get_mongo_db() -> Generator[Database, None, None]:
    """FastAPI Dependency Injection용"""
    yield db_manager.get_db()


def get_mongo_client_direct() -> MongoClient:
    """직접 접근용 헬퍼"""
    return db_manager.get_client()


def get_prod_mongo_client() -> MongoClient:
    """
    Production MongoDB 클라이언트를 생성하여 반환.
    로컬 환경에서 데이터 복제 시에만 사용.
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
        mongo_uri = (
            f"mongodb://{user}:{password}@{host}:{port}/?authSource={auth_source}"
        )
    else:
        mongo_uri = f"mongodb://{host}:{port}/"

    try:
        client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=10000,
            maxPoolSize=10,
        )
        client.admin.command("ping")
        logger.info(
            f"Production MongoDB client created: host={host}:{port} "
            f"user={user or 'none'}"
        )
        return client
    except PyMongoError as e:
        logger.error(f"Failed to connect to production MongoDB: {e}")
        raise



