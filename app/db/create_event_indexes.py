"""
MongoDB 인덱스 생성 스크립트.

recommendation_events 컬렉션에 필요한 인덱스를 생성합니다.
"""

from pymongo import ASCENDING, DESCENDING
from app.db.mongodb import get_mongo_db_sync
from app.core.constants import (
    COLLECTION_RECOMMENDATION_EVENTS,
    TTL_RECOMMENDATION_EVENTS_SECONDS,
)


def create_recommendation_events_indexes():
    """recommendation_events 컬렉션 인덱스 생성"""
    db = get_mongo_db_sync()
    collection = db[COLLECTION_RECOMMENDATION_EVENTS]

    print(f"Creating indexes for {COLLECTION_RECOMMENDATION_EVENTS}...")

    # 1. 사용자별 이벤트 조회 (최신순)
    collection.create_index(
        [("user_id", ASCENDING), ("timestamp", DESCENDING)],
        name="user_timestamp_idx",
    )
    print("✓ Created index: user_timestamp_idx")

    # 2. 세션별 이벤트 조회 (시간순)
    collection.create_index(
        [("session_id", ASCENDING), ("timestamp", ASCENDING)],
        name="session_timestamp_idx",
    )
    print("✓ Created index: session_timestamp_idx")

    # 3. 논문별 이벤트 통계
    collection.create_index(
        [("paper_id", ASCENDING), ("activity_type", ASCENDING)],
        name="paper_activity_idx",
    )
    print("✓ Created index: paper_activity_idx")

    # 4. TTL 인덱스 (90일 후 자동 삭제)
    collection.create_index(
        [("timestamp", ASCENDING)],
        name="timestamp_ttl_idx",
        expireAfterSeconds=TTL_RECOMMENDATION_EVENTS_SECONDS,
    )
    print(f"✓ Created TTL index: timestamp_ttl_idx (expire after {TTL_RECOMMENDATION_EVENTS_SECONDS}s)")

    print(f"\nAll indexes created for {COLLECTION_RECOMMENDATION_EVENTS}")


if __name__ == "__main__":
    create_recommendation_events_indexes()
