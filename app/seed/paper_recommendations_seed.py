"""
Dev 환경용 Mock paper_recommendations 데이터 생성 스크립트.

500개의 추천 로그를 생성합니다.
"""

from __future__ import annotations
import logging
import random
from datetime import datetime, timedelta
from pymongo.database import Database
from app.core.constants import COLLECTION_PAPER_RECOMMENDATIONS

from app.db.mongodb import get_mongo_db
from app.core.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NUM_RECOMMENDATIONS = 500


def seed_paper_recommendations(db: Database) -> int:
    """
    500개의 mock paper_recommendations를 생성합니다.

    - user_id: 랜덤 (1~500)
    - paper_id: papers 컬렉션에서 샘플링
    - recommendation_type: "rule_based" 또는 "rl_based"
    - session_id: 그룹별로 동일 (한 세션에 6개씩)
    - score, features, was_clicked 등
    
    Returns:
        생성된 recommendations 개수
    """
    # papers 컬렉션에서 실제 논문 ID들 샘플링
    papers_coll = db[settings.mongo_collection]
    paper_ids = list(papers_coll.find({}, {"_id": 1}).limit(1000))

    if not paper_ids:
        logger.error("❌ No papers found in collection. Please load papers first.")
        return 0

    logger.info(f"Found {len(paper_ids)} papers for recommendation references")

    recommendations_coll = db[COLLECTION_PAPER_RECOMMENDATIONS]

    # 기존 recommendations 개수 확인
    existing_count = recommendations_coll.count_documents({})
    logger.info(f"Existing recommendations: {existing_count}")

    recommendations = []
    now = datetime.utcnow()

    # 세션 그룹별로 생성 (한 세션에 6개씩)
    num_sessions = NUM_RECOMMENDATIONS // 6
    session_counter = 0

    for session_idx in range(num_sessions):
        # 랜덤 사용자 ID
        user_id = random.randint(1, 500)
        
        # 세션 ID 생성
        import uuid
        session_id = str(uuid.uuid4())
        
        # 랜덤 추천 타입
        recommendation_type = random.choice(["rule_based", "rule_based", "rule_based", "rl_based"])  # 75% rule_based
        
        # 랜덤 timestamp (최근 30일)
        days_ago = random.randint(0, 30)
        recommended_at = now - timedelta(days=days_ago, hours=random.randint(0, 23))
        
        # 한 세션에 6개 추천
        session_papers = random.sample(paper_ids, 6)
        
        for rank, paper in enumerate(session_papers):
            paper_id = paper["_id"]
            
            # 룰베이스 점수 생성
            interest_score = round(random.uniform(0.0, 5.0), 2)
            popularity_score = round(random.uniform(0.0, 3.0), 2)
            recency_score = round(random.uniform(0.0, 2.0), 2)
            personalization_score = round(random.uniform(0.0, 4.0), 2)
            
            total_score = round(
                interest_score * 0.4 + popularity_score * 0.2 +
                recency_score * 0.1 + personalization_score * 0.3,
                2
            )
            
            # 추천 이유
            reasons = []
            if interest_score > 3.0:
                reasons.append("관심사와 높은 관련성")
            if popularity_score > 1.5:
                reasons.append("인기 논문")
            if personalization_score > 2.0:
                reasons.append("개인 취향과 일치")
            if not reasons:
                reasons.append("다양한 주제의 논문")
            
            # 클릭 여부 (20% 확률)
            was_clicked = random.random() < 0.2
            
            recommendation = {
                "user_id": user_id,
                "paper_id": paper_id,
                "recommendation_type": recommendation_type,
                "score": total_score,
                "session_id": session_id,
                "features": {
                    "interest_score": interest_score,
                    "popularity_score": popularity_score,
                    "recency_score": recency_score,
                    "personalization_score": personalization_score,
                },
                "context": {"reasons": reasons},
                "was_clicked": was_clicked,
                "recommended_at": recommended_at,
            }
            
            if was_clicked:
                # 클릭 시간은 추천 후 몇 분 뒤
                recommendation["clicked_at"] = recommended_at + timedelta(minutes=random.randint(1, 30))
            
            recommendations.append(recommendation)
            session_counter += 1

        if (session_idx + 1) % 10 == 0:
            logger.info(f"Generated {session_counter}/{NUM_RECOMMENDATIONS} recommendations...")

    # Bulk insert
    if recommendations:
        result = recommendations_coll.insert_many(recommendations, ordered=False)
        logger.info(f"✅ Total {len(result.inserted_ids)} recommendations created!")
        return len(result.inserted_ids)

    return 0


def seed_paper_recommendations_standalone() -> None:
    """
    독립적으로 실행 가능한 함수 (CLI에서 호출용).
    """
    db = next(get_mongo_db())
    seed_paper_recommendations(db)


if __name__ == "__main__":
    seed_paper_recommendations_standalone()
