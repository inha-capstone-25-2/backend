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
    """컬렉션별 인덱스 정의를 반환한다.

    Args:
        papers_collection_name: papers 컬렉션 이름.

    Returns:
        컬렉션 이름을 키로, IndexModel 리스트를 값으로 하는 딕셔너리.
    """
    return {
        COLLECTION_SEARCH_HISTORY: [
            IndexModel(
                [("searched_at", ASCENDING)],
                name="ttl_searched_at",
                expireAfterSeconds=TTL_SEARCH_HISTORY_SECONDS,
            )
        ],

        COLLECTION_USER_ACTIVITIES: [
            IndexModel(
                [("timestamp", ASCENDING)],
                name="ttl_timestamp",
                expireAfterSeconds=TTL_USER_ACTIVITIES_SECONDS,
            ),
            IndexModel(
                [("user_id", ASCENDING), ("activity_type", ASCENDING), ("timestamp", DESCENDING)],
                name="user_activity_type_timestamp_idx",
            ),
        ],

        COLLECTION_RECOMMENDATION_INTERACTIONS: [
            IndexModel(
                [("created_at", ASCENDING)],
                name="ttl_created_at",
                expireAfterSeconds=TTL_RECOMMENDATION_INTERACTIONS_SECONDS,
            )
        ],

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

        papers_collection_name: [
            # summary.ko 인덱스: 요약되지 않은 논문 조회 최적화
            IndexModel(
                [("summary.ko", ASCENDING)],
                name="summary_ko_idx",
            ),
            # update_date 인덱스: 최신 논문 조회 최적화
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
    """정의된 모든 인덱스를 생성한다.

    이미 존재하는 인덱스는 건너뜁니다 (멱등성 보장).

    Args:
        db: MongoDB Database 인스턴스.
        skip_papers: True일 경우 papers 컬렉션 인덱스 생성을 스킵.
    """
    logger.info("Starting MongoDB index creation...")
    
    definitions = get_index_definitions(settings.mongo_collection)
    
    for collection_name, indexes in definitions.items():
        if skip_papers and collection_name == settings.mongo_collection:
            logger.info(f"Skipping index creation for {collection_name} (will be created after data load)")
            continue
            
        try:
            collection = db[collection_name]
            result = collection.create_indexes(indexes)
            logger.info(f"Indexes created for {collection_name}: {result}")
        except Exception as e:
            logger.error(f"Failed to create indexes for {collection_name}: {e}")
            
    logger.info("MongoDB index creation completed.")


def sync_indexes(db: Database, skip_papers: bool = False, dry_run: bool = False) -> dict:
    """
    코드에 정의된 인덱스와 DB의 인덱스를 동기화합니다.
    
    - 코드에 없는 인덱스 → 삭제 (deprecated 정리)
    - 코드에만 있는 인덱스 → 생성
    - _id 인덱스는 건드리지 않음
    
    Args:
        db: MongoDB Database 인스턴스
        skip_papers: True일 경우 papers 컬렉션 스킵
        dry_run: True일 경우 실제 변경 없이 변경 예정 사항만 반환
        
    Returns:
        {"dropped": [...], "created": [...], "unchanged": [...]}
    """
    logger.info(f"Starting MongoDB index sync... (dry_run={dry_run})")
    
    definitions = get_index_definitions(settings.mongo_collection)
    result = {"dropped": [], "created": [], "unchanged": []}
    
    for collection_name, defined_indexes in definitions.items():
        if skip_papers and collection_name == settings.mongo_collection:
            logger.info(f"Skipping sync for {collection_name}")
            continue
        
        collection = db[collection_name]
        
        defined_names = {idx.document.get("name") for idx in defined_indexes}
        
        existing_indexes = collection.index_information()
        existing_names = {name for name in existing_indexes.keys() if name != "_id_"}
        
        to_drop = existing_names - defined_names
        for idx_name in to_drop:
            logger.info(f"[{collection_name}] Dropping deprecated index: {idx_name}")
            result["dropped"].append(f"{collection_name}.{idx_name}")
            if not dry_run:
                try:
                    collection.drop_index(idx_name)
                except Exception as e:
                    logger.error(f"Failed to drop index {idx_name}: {e}")
        
        # 생성할 인덱스: 코드에만 있고 DB에는 없는 것
        to_create = defined_names - existing_names
        for idx in defined_indexes:
            idx_name = idx.document.get("name")
            if idx_name in to_create:
                logger.info(f"[{collection_name}] Creating new index: {idx_name}")
                result["created"].append(f"{collection_name}.{idx_name}")
                if not dry_run:
                    try:
                        collection.create_indexes([idx])
                    except Exception as e:
                        logger.error(f"Failed to create index {idx_name}: {e}")
        
        unchanged = defined_names & existing_names
        for idx_name in unchanged:
            result["unchanged"].append(f"{collection_name}.{idx_name}")
    
    logger.info(f"Index sync completed: {len(result['dropped'])} dropped, {len(result['created'])} created, {len(result['unchanged'])} unchanged")
    return result
