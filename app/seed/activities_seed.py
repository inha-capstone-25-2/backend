"""
Dev 환경용 Mock user_activities 데이터 생성 스크립트.

1,000개의 사용자 활동 로그를 생성합니다.
"""
from __future__ import annotations
import logging
import random
from datetime import datetime, timedelta
from pymongo.database import Database
from bson import ObjectId

from app.db.mongodb import get_mongo_db
from app.core.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NUM_ACTIVITIES = 1000

ACTIVITY_TYPES = ["view", "search", "bookmark", "unbookmark"]


def seed_activities(db: Database) -> int:
    """
    1,000개의 mock user_activities를 생성합니다.
    
    - activity_type: 랜덤 ("view", "search", "bookmark", "unbookmark")
    - 랜덤 사용자 ID (1~500)
    - 랜덤 paper_id (activity_type이 "view", "bookmark" 등일 때)
    - 랜덤 timestamp (최근 3개월 이내)
    
    Returns:
        생성된 activities 개수
    """
    # papers 컬렉션에서 실제 논문 ID들 샘플링
    papers_coll = db[settings.mongo_collection]
    paper_ids = list(papers_coll.find({}, {"_id": 1}).limit(1000))
    
    if not paper_ids:
        logger.error("❌ No papers found in collection. Please load papers first.")
        return 0
    
    logger.info(f"Found {len(paper_ids)} papers for activity references")
    
    activities_coll = db["user_activities"]
    
    # 기존 activities 개수 확인
    existing_count = activities_coll.count_documents({})
    logger.info(f"Existing activities: {existing_count}")
    
    activities = []
    now = datetime.utcnow()
    
    for i in range(NUM_ACTIVITIES):
        # 랜덤 사용자 ID (1~500)
        user_id = random.randint(1, 500)
        
        # 랜덤 activity_type
        activity_type = random.choice(ACTIVITY_TYPES)
        
        # 랜덤 timestamp (최근 3개월)
        days_ago = random.randint(0, 90)
        timestamp = now - timedelta(days=days_ago, hours=random.randint(0, 23))
        
        # paper_id (activity_type이 "view", "bookmark", "unbookmark"일 때)
        paper_id = None
        if activity_type in ["view", "bookmark", "unbookmark"]:
            paper = random.choice(paper_ids)
            paper_id = paper["_id"]  # ObjectId로 저장
        
        activity = {
            "user_id": user_id,
            "activity_type": activity_type,
            "timestamp": timestamp,
        }
        
        if paper_id:
            activity["paper_id"] = paper_id  # ObjectId 그대로 저장
        
        # metadata (선택적)
        if activity_type == "search":
            activity["metadata"] = {
                "query": random.choice(["transformer", "GAN", "neural network", "deep learning"])
            }
        
        activities.append(activity)
        
        if (i + 1) % 200 == 0:
            logger.info(f"Generated {i + 1}/{NUM_ACTIVITIES} activities...")
    
    # Bulk insert
    if activities:
        result = activities_coll.insert_many(activities, ordered=False)
        logger.info(f"✅ Total {len(result.inserted_ids)} activities created!")
        return len(result.inserted_ids)
    
    return 0


def seed_activities_standalone() -> None:
    """
    독립적으로 실행 가능한 함수 (CLI에서 호출용).
    """
    db = next(get_mongo_db())
    seed_activities(db)


if __name__ == "__main__":
    seed_activities_standalone()
