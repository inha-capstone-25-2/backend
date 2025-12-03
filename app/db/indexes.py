"""
MongoDB 인덱스 정의 및 생성 유틸리티.

모든 컬렉션의 인덱스를 이곳에서 중앙 관리합니다.
애플리케이션 시작 시 ensure_indexes()를 호출하여 인덱스를 생성합니다.
"""

import logging
from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.database import Database

from app.core.constants import (
    COLLECTION_SEARCH_HISTORY,
    COLLECTION_USER_ACTIVITIES,
    COLLECTION_RECOMMENDATION_INTERACTIONS,
    COLLECTION_RECOMMENDATION_EVENTS,
    TTL_SEARCH_HISTORY_SECONDS,
    TTL_USER_ACTIVITIES_SECONDS,
    TTL_RECOMMENDATION_INTERACTIONS_SECONDS,
    TTL_RECOMMENDATION_EVENTS_SECONDS,
)
from app.core.settings import settings

logger = logging.getLogger(__name__)

def get_index_definitions(papers_collection_name: str) -> dict:
    """
    컬렉션별 인덱스 정의를 반환합니다.
    
    Returns:
        dict: {collection_name: [IndexModel, ...]}
    """
    return {
        # 1. Search History (TTL)
        COLLECTION_SEARCH_HISTORY: [
            IndexModel(
                [("searched_at", ASCENDING)],
                name="ttl_searched_at",
                expireAfterSeconds=TTL_SEARCH_HISTORY_SECONDS,
            )
        ],

        # 2. User Activities (TTL)
        COLLECTION_USER_ACTIVITIES: [
            IndexModel(
                [("timestamp", ASCENDING)],
                name="ttl_timestamp",
                expireAfterSeconds=TTL_USER_ACTIVITIES_SECONDS,
            )
        ],

        # 3. Recommendation Interactions (TTL)
        COLLECTION_RECOMMENDATION_INTERACTIONS: [
            IndexModel(
                [("created_at", ASCENDING)],
                name="ttl_created_at",
                expireAfterSeconds=TTL_RECOMMENDATION_INTERACTIONS_SECONDS,
            )
        ],

        # 4. Recommendation Events (RL Data)
        COLLECTION_RECOMMENDATION_EVENTS: [
            # 사용자별 조회 (최신순)
            IndexModel(
                [("user_id", ASCENDING), ("timestamp", DESCENDING)],
                name="user_timestamp_idx",
            ),
            # 세션별 조회 (시간순)
            IndexModel(
                [("session_id", ASCENDING), ("timestamp", ASCENDING)],
                name="session_timestamp_idx",
            ),
            # 논문별 통계
            IndexModel(
                [("paper_id", ASCENDING), ("activity_type", ASCENDING)],
                name="paper_activity_idx",
            ),
            # TTL
            IndexModel(
                [("timestamp", ASCENDING)],
                name="ttl_timestamp",
                expireAfterSeconds=TTL_RECOMMENDATION_EVENTS_SECONDS,
            ),
        ],

        # 5. Papers (검색 및 추천용)
        papers_collection_name: [
            # 관심사 필터링
            IndexModel(
                [("categories", ASCENDING)],
                name="categories_only",
                background=True,
            ),
            # 인기도 정렬
            IndexModel(
                [("view_count", DESCENDING), ("bookmark_count", DESCENDING)],
                name="popularity_sort",
                background=True,
            ),
            # 카테고리 + 인기도 (검색 최적화)
            IndexModel(
                [("categories", ASCENDING), ("view_count", DESCENDING)],
                name="categories_view_count",
                background=True,
            ),
            IndexModel(
                [("categories", ASCENDING), ("bookmark_count", DESCENDING)],
                name="categories_bookmark_count",
                background=True,
            ),
            # Text Search Index (Fallback용)
            IndexModel(
                [
                    ("title", "text"),
                    ("summary.en", "text"),
                    ("authors", "text"),
                ],
                name="text_search_idx",
                weights={"title": 3, "authors": 2, "summary.en": 1},
                background=True,
            ),
        ],
    }


def ensure_indexes(db: Database) -> None:
    """
    정의된 모든 인덱스를 생성합니다.
    이미 존재하는 인덱스는 건너뜁니다 (멱등성 보장).
    """
    logger.info("Starting MongoDB index creation...")
    
    definitions = get_index_definitions(settings.mongo_collection)
    
    for collection_name, indexes in definitions.items():
        try:
            collection = db[collection_name]
            # 인덱스 생성 (create_indexes는 여러 개를 한 번에 생성)
            result = collection.create_indexes(indexes)
            logger.info(f"Indexes created for {collection_name}: {result}")
        except Exception as e:
            logger.error(f"Failed to create indexes for {collection_name}: {e}")
            
    logger.info("MongoDB index creation completed.")
