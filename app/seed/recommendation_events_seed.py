"""
Dev 환경용 Mock recommendation_events 데이터 생성 스크립트.

추천 이벤트(expose, click, bookmark, detail_view, close)를 생성합니다.
"""

from __future__ import annotations
import logging
import random
from datetime import datetime, timedelta
from pymongo.database import Database
from app.core.constants import COLLECTION_RECOMMENDATION_EVENTS, COLLECTION_PAPER_RECOMMENDATIONS

from app.db.mongodb import get_mongo_db
from app.core.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_recommendation_events(db: Database) -> int:
    """
    recommendation_events를 생성합니다.
    
    paper_recommendations에서 세션별로:
    1. session_context 이벤트 1개 (RL 메타데이터)
    2. expose 이벤트 6개 (세션별 추천 논문)
    3. click, detail_view, bookmark, close 이벤트 (확률적)
    
    Returns:
        생성된 events 개수
    """
    # papers 컬렉션에서 실제 논문 ID들 샘플링
    papers_coll = db[settings.mongo_collection]
    paper_ids = list(papers_coll.find({}, {"_id": 1}).limit(500))
    
    if not paper_ids:
        logger.error("❌ No papers found. Please load papers first.")
        return 0
    
    # paper_recommendations에서 세션 정보 가져오기
    recommendations_coll = db[COLLECTION_PAPER_RECOMMENDATIONS]
    
    # 세션별로 그룹화
    pipeline = [
        {"$group": {
            "_id": "$session_id",
            "user_id": {"$first": "$user_id"},
            "recommended_at": {"$first": "$recommended_at"},
            "papers": {"$push": {
                "paper_id": "$paper_id",
                "score": "$score",
                "features": "$features"
            }}
        }},
        {"$limit": 50}  # 50개 세션만
    ]
    
    sessions = list(recommendations_coll.aggregate(pipeline))
    
    if not sessions:
        logger.warning("⚠️ No recommendations found. Creating events without sessions.")
        sessions = []
    
    events_coll = db[COLLECTION_RECOMMENDATION_EVENTS]
    existing_count = events_coll.count_documents({})
    logger.info(f"Existing events: {existing_count}")
    
    events = []
    
    for session in sessions:
        session_id = session["_id"]
        user_id = session["user_id"]
        recommended_at = session["recommended_at"]
        papers = session["papers"]
        
        if not papers:
            continue
        
        all_candidate_ids = [p["paper_id"] for p in papers]
        candidates_features = {p["paper_id"]: p["features"] for p in papers}
        candidates_scores = {p["paper_id"]: p["score"] for p in papers}
        final_display = all_candidate_ids[:6]  # 상위 6개
        
        session_context_event = {
            "user_id": user_id,
            "paper_id": "",
            "activity_type": "session_context",
            "timestamp": recommended_at,
            "session_id": session_id,
            "metadata": {
                "candidates": all_candidate_ids,
                "candidates_features": candidates_features,
                "candidates_scores": candidates_scores,
                "final_display": final_display,
            }
        }
        events.append(session_context_event)
        
        for idx, paper_id in enumerate(final_display):
            expose_event = {
                "user_id": user_id,
                "paper_id": paper_id,
                "activity_type": "expose",
                "timestamp": recommended_at,
                "session_id": session_id,
                "metadata": {"position": idx}
            }
            events.append(expose_event)
        
        if random.random() < 0.3 and final_display:
            clicked_paper = final_display[0]
            click_time = recommended_at + timedelta(seconds=random.randint(5, 60))
            
            # Click 이벤트
            click_event = {
                "user_id": user_id,
                "paper_id": clicked_paper,
                "activity_type": "click",
                "timestamp": click_time,
                "session_id": session_id,
                "metadata": {"position": 0}
            }
            events.append(click_event)
            
            # Detail View 이벤트 (클릭 후 체류)
            dwell_time_ms = random.randint(10000, 120000)  # 10초~2분
            detail_view_event = {
                "user_id": user_id,
                "paper_id": clicked_paper,
                "activity_type": "detail_view",
                "timestamp": click_time + timedelta(milliseconds=100),
                "session_id": session_id,
                "metadata": {"dwell_time_ms": dwell_time_ms}
            }
            events.append(detail_view_event)
            
            # 20% 확률로 북마크
            if random.random() < 0.2:
                bookmark_time = click_time + timedelta(seconds=random.randint(10, 60))
                bookmark_event = {
                    "user_id": user_id,
                    "paper_id": clicked_paper,
                    "activity_type": "bookmark",
                    "timestamp": bookmark_time,
                    "session_id": session_id,
                    "metadata": {}
                }
                events.append(bookmark_event)
            
            # Close 이벤트
            close_time = click_time + timedelta(milliseconds=dwell_time_ms)
            close_event = {
                "user_id": user_id,
                "paper_id": clicked_paper,
                "activity_type": "close",
                "timestamp": close_time,
                "session_id": session_id,
                "metadata": {"dwell_time_ms": dwell_time_ms}
            }
            events.append(close_event)
    
    # Bulk insert
    if events:
        result = events_coll.insert_many(events, ordered=False)
        logger.info(f"✅ Total {len(result.inserted_ids)} recommendation events created!")
        return len(result.inserted_ids)
    
    return 0


def seed_recommendation_events_standalone() -> None:
    """
    독립적으로 실행 가능한 함수 (CLI에서 호출용).
    """
    db = next(get_mongo_db())
    seed_recommendation_events(db)


if __name__ == "__main__":
    seed_recommendation_events_standalone()
