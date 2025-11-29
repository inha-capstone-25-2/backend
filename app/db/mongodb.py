import logging
from typing import Generator, Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError
from app.core.settings import settings
from app.core.constants import (
    COLLECTION_SEARCH_HISTORY,
    COLLECTION_USER_ACTIVITIES,
    COLLECTION_RECOMMENDATION_INTERACTIONS,
    TTL_SEARCH_HISTORY_SECONDS,
    TTL_USER_ACTIVITIES_SECONDS,
    TTL_RECOMMENDATION_INTERACTIONS_SECONDS,
)


logger = logging.getLogger(__name__)


class MongoDBManager:
    """
    MongoDB 연결을 관리하는 싱글톤 스타일 클래스.
    """

    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None

    def connect(self) -> None:
        """MongoDB 연결 초기화"""
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

            self._create_indexes()

        except PyMongoError as e:
            logger.error(f"MongoDB initialization failed: {e}")
            self.client = None
            self.db = None

    def _create_indexes(self) -> None:
        """TTL 인덱스 등 필요한 인덱스 생성"""
        if not self.db:
            return

        try:
            # search_history: 30일 후 자동 삭제
            self.db[COLLECTION_SEARCH_HISTORY].create_index(
                "searched_at",
                expireAfterSeconds=TTL_SEARCH_HISTORY_SECONDS,
                name="ttl_searched_at",
            )
            logger.info("TTL index created for search_history (30 days)")

            # user_activities: 90일 후 자동 삭제
            self.db[COLLECTION_USER_ACTIVITIES].create_index(
                "timestamp",
                expireAfterSeconds=TTL_USER_ACTIVITIES_SECONDS,
                name="ttl_timestamp",
            )
            logger.info("TTL index created for user_activities (90 days)")

            # recommendation_interactions: 60일 후 자동 삭제
            self.db[COLLECTION_RECOMMENDATION_INTERACTIONS].create_index(
                "created_at",
                expireAfterSeconds=TTL_RECOMMENDATION_INTERACTIONS_SECONDS,
                name="ttl_created_at",
            )
            logger.info("TTL index created for recommendation_interactions (60 days)")

            # papers 컬렉션: 추천 시스템용 및 검색 API용 인덱스
            papers_collection = self.db[settings.mongo_collection]
            
            # categories 인덱스 (관심사 기반 필터링)
            papers_collection.create_index(
                [("categories", 1)],
                name="categories_only",
                background=True
            )
            logger.info("Index created for papers: categories (recommendation)")

            # view_count, bookmark_count 복합 인덱스 (인기도 정렬)
            papers_collection.create_index(
                [("view_count", -1), ("bookmark_count", -1)],
                name="popularity_sort",
                background=True
            )
            logger.info("Index created for papers: view_count + bookmark_count (popularity)")

            # categories + view_count 복합 인덱스 (검색 API용)
            papers_collection.create_index(
                [("categories", 1), ("view_count", -1)],
                name="categories_view_count",
                background=True
            )
            logger.info("Index created for papers: categories + view_count (search API)")

            # categories + bookmark_count 복합 인덱스 (검색 API용)
            papers_collection.create_index(
                [("categories", 1), ("bookmark_count", -1)],
                name="categories_bookmark_count",
                background=True
            )
            logger.info("Index created for papers: categories + bookmark_count (search API)")

        except Exception as e:
            logger.warning(f"Index creation failed (may already exist): {e}")


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
    (이 함수는 별도의 연결을 생성하므로 Manager와 무관하게 유지)
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
