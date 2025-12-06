"""MongoDB 데이터베이스 연결 설정.

MongoDB 클라이언트를 초기화하고 연결을 관리합니다.
싱글톤 패턴으로 연결을 재사용합니다.
"""

import logging
from typing import Generator, Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError
from app.core.settings import settings


logger = logging.getLogger(__name__)


class MongoDBManager:
    """MongoDB 연결을 관리하는 싱글톤 스타일 클래스.

    Attributes:
        client: MongoDB 클라이언트 인스턴스.
        db: MongoDB 데이터베이스 인스턴스.
    """

    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None

    def connect(self, skip_indexes: bool = False) -> None:
        """MongoDB 연결을 초기화한다.

        Args:
            skip_indexes: True이면 인덱스 생성을 건너뜀.

        Raises:
            PyMongoError: MongoDB 연결 실패 시.
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
        """필요한 인덱스를 생성하고 동기화한다."""
        if self.db is None:
            return

        from app.db.indexes import sync_indexes

        sync_indexes(self.db, skip_papers=False)


    def close(self) -> None:
        """MongoDB 연결을 종료한다."""
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
        """Database 인스턴스를 반환한다.

        Returns:
            MongoDB Database 인스턴스.

        Raises:
            RuntimeError: MongoDB가 초기화되지 않은 경우.
        """
        if self.db is None:
            raise RuntimeError("MongoDB is not initialized. Call connect() first.")
        return self.db

    def get_client(self) -> MongoClient:
        """MongoClient 인스턴스를 반환한다.

        Returns:
            MongoClient 인스턴스.

        Raises:
            RuntimeError: MongoDB가 초기화되지 않은 경우.
        """
        if self.client is None:
            raise RuntimeError("MongoDB is not initialized. Call connect() first.")
        return self.client


db_manager = MongoDBManager()


def init_mongo(skip_indexes: bool = False) -> None:
    """애플리케이션 시작 시 MongoDB를 초기화한다.

    Args:
        skip_indexes: True이면 인덱스 생성을 건너뜀.
    """
    db_manager.connect(skip_indexes=skip_indexes)


def close_mongo() -> None:
    """애플리케이션 종료 시 MongoDB 연결을 종료한다."""
    db_manager.close()


def get_mongo_db() -> Generator[Database, None, None]:
    """FastAPI Dependency Injection용 MongoDB Database를 반환한다.

    Yields:
        MongoDB Database 인스턴스.
    """
    yield db_manager.get_db()


def get_mongo_client_direct() -> MongoClient:
    """직접 접근용 MongoClient를 반환한다.

    Returns:
        MongoClient 인스턴스.
    """
    return db_manager.get_client()


def get_prod_mongo_client() -> MongoClient:
    """Production MongoDB 클라이언트를 생성한다.

    로컬 환경에서 데이터 복제 시에만 사용됩니다.

    Returns:
        Production MongoDB 클라이언트.

    Raises:
        RuntimeError: PROD_MONGO_HOST가 설정되지 않은 경우.
        PyMongoError: MongoDB 연결 실패 시.
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



