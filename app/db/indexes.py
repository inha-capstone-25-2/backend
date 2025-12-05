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

        # 2. User Activities (TTL + 추천 조회 최적화)
        COLLECTION_USER_ACTIVITIES: [
            IndexModel(
                [("timestamp", ASCENDING)],
                name="ttl_timestamp",
                expireAfterSeconds=TTL_USER_ACTIVITIES_SECONDS,
            ),
            # 사용자별 활동 조회 최적화 (추천 시스템용)
            IndexModel(
                [("user_id", ASCENDING), ("activity_type", ASCENDING), ("timestamp", DESCENDING)],
                name="user_activity_type_timestamp_idx",
            ),
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

        # 5. Papers (검색은 Elasticsearch 사용)
        papers_collection_name: [
            # summary.ko 인덱스: 요약되지 않은 논문 조회 최적화
            IndexModel(
                [("summary.ko", ASCENDING)],
                name="summary_ko_idx",
                sparse=True,  # null 값이 많은 경우 효율적
            ),
            # update_date 인덱스: 최신 논문 조회 최적화 (sort by update_date DESC)
            IndexModel(
                [("update_date", DESCENDING)],
                name="update_date_desc_idx",
            ),
            # 카테고리 기반 추천 쿼리 최적화
            IndexModel(
                [("categories", ASCENDING), ("view_count", DESCENDING), ("bookmark_count", DESCENDING)],
                name="categories_popularity_idx",
            ),
            # 인기 논문 조회 (관심사 없는 사용자용)
            IndexModel(
                [("view_count", DESCENDING), ("bookmark_count", DESCENDING)],
                name="popularity_idx",
            ),
        ],
    }


def ensure_indexes(db: Database, skip_papers: bool = False) -> None:
    """
    정의된 모든 인덱스를 생성합니다.
    이미 존재하는 인덱스는 건너뜁니다 (멱등성 보장).
    
    Args:
        db: MongoDB Database 인스턴스
        skip_papers: True일 경우 papers 컬렉션 인덱스 생성을 스킵 (기본값: False)
    """
    logger.info("Starting MongoDB index creation...")
    
    definitions = get_index_definitions(settings.mongo_collection)
    
    for collection_name, indexes in definitions.items():
        # papers 컬렉션 스킵 (데이터 적재 후 생성)
        if skip_papers and collection_name == settings.mongo_collection:
            logger.info(f"Skipping index creation for {collection_name} (will be created after data load)")
            continue
            
        try:
            collection = db[collection_name]
            # 인덱스 생성 (create_indexes는 여러 개를 한 번에 생성)
            result = collection.create_indexes(indexes)
            logger.info(f"Indexes created for {collection_name}: {result}")
        except Exception as e:
            logger.error(f"Failed to create indexes for {collection_name}: {e}")
            
    logger.info("MongoDB index creation completed.")
