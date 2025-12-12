"""
Dev 환경용 Mock recommendation_interactions 데이터 생성 스크립트.

클릭된 추천 논문에 대한 상호작용 데이터(체류 시간, 스크롤 깊이, 북마크 여부)를 생성합니다.
"""

from __future__ import annotations
import logging
import random
from datetime import datetime, timedelta
from bson import ObjectId
from pymongo.database import Database
from app.core.constants import (
    COLLECTION_RECOMMENDATION_INTERACTIONS,
    COLLECTION_PAPER_RECOMMENDATIONS,
)

from app.db.mongodb import get_mongo_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_recommendation_interactions(db: Database) -> int:
    """
    클릭된 추천에 대한 mock recommendation_interactions를 생성합니다.

    paper_recommendations에서 was_clicked=True인 문서를 기반으로:
    - dwell_time_seconds: 5~300초 랜덤
    - scroll_depth_percent: 10~100% 랜덤
    - bookmarked: 20% 확률로 True
    
    Returns:
        생성된 interactions 개수
    """
    recommendations_coll = db[COLLECTION_PAPER_RECOMMENDATIONS]
    interactions_coll = db[COLLECTION_RECOMMENDATION_INTERACTIONS]

    existing_count = interactions_coll.count_documents({})
    logger.info(f"Existing recommendation_interactions: {existing_count}")

    clicked_recommendations = list(recommendations_coll.find({"was_clicked": True}))
    
    if not clicked_recommendations:
        logger.warning("⚠️ No clicked recommendations found. Please run paper_recommendations_seed.py first.")
        return 0

    logger.info(f"Found {len(clicked_recommendations)} clicked recommendations")

    interactions = []
    now = datetime.utcnow()

    for rec in clicked_recommendations:
        rec_id = str(rec["_id"])
        user_id = rec["user_id"]
        paper_id = rec["paper_id"]
        
        clicked_at = rec.get("clicked_at", now - timedelta(days=random.randint(0, 30)))

        if random.random() < 0.3:
            dwell_time_seconds = random.randint(60, 300)
        else:
            dwell_time_seconds = random.randint(5, 60)
        
        if dwell_time_seconds > 120:
            scroll_depth_percent = random.randint(60, 100)
        elif dwell_time_seconds > 30:
            scroll_depth_percent = random.randint(30, 80)
        else:
            scroll_depth_percent = random.randint(10, 50)
        
        bookmark_probability = 0.2 if dwell_time_seconds < 60 else 0.35
        bookmarked = random.random() < bookmark_probability
        
        created_at = clicked_at
        updated_at = clicked_at + timedelta(seconds=dwell_time_seconds)
        
        interaction = {
            "recommendation_id": rec_id,
            "user_id": user_id,
            "paper_id": paper_id,
            "dwell_time_seconds": dwell_time_seconds,
            "scroll_depth_percent": scroll_depth_percent,
            "bookmarked": bookmarked,
            "created_at": created_at,
            "updated_at": updated_at,
        }
        
        interactions.append(interaction)

    if not interactions:
        logger.warning("⚠️ No interactions generated.")
        return 0

    try:
        result = interactions_coll.insert_many(interactions, ordered=False)
        logger.info(f"✅ Total {len(result.inserted_ids)} recommendation_interactions created!")
        return len(result.inserted_ids)
    except Exception as e:
        logger.error(f"❌ Failed to insert interactions: {e}")
        return 0


def seed_recommendation_interactions_standalone() -> None:
    """
    독립적으로 실행 가능한 함수 (CLI에서 호출용).
    """
    db = next(get_mongo_db())
    seed_recommendation_interactions(db)


if __name__ == "__main__":
    seed_recommendation_interactions_standalone()
