"""
추천 시스템 API 엔드포인트.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pymongo.database import Database
from datetime import datetime
import logging
from typing import List

from app.db.postgres import get_db
from app.db.mongodb import get_mongo_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.recommendation import RecommendationResponse, RecommendationItem, ScoreBreakdown
from app.utils.rule_based_recommender import RuleBasedRecommender
from app.utils.mongodb import serialize_object_id

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
logger = logging.getLogger(__name__)


def _log_recommendation(
    db: Database,
    user_id: int,
    recommendations: List[dict],
    recommendation_type: str = "rule_based"
) -> None:
    """
    추천 결과를 MongoDB에 로깅.
    
    Args:
        db: MongoDB Database
        user_id: 사용자 ID
        recommendations: 추천 결과 리스트
        recommendation_type: 추천 타입
    """
    collection = db["paper_recommendations"]
    
    for rec in recommendations:
        paper_id = rec.get("paper_id")
        breakdown = rec.get("breakdown", {})
        reasons = rec.get("reasons", [])
        
        log_doc = {
            "user_id": user_id,
            "paper_id": paper_id,
            "recommendation_type": recommendation_type,
            "score": rec.get("total_score", 0.0),
            "features": {
                "interest_score": breakdown.get("interest_score", 0.0),
                "popularity_score": breakdown.get("popularity_score", 0.0),
                "recency_score": breakdown.get("recency_score", 0.0),
                "personalization_score": breakdown.get("personalization_score", 0.0)
            },
            "context": {
                "reasons": reasons
            },
            "was_clicked": False,  # 초기값
            "recommended_at": datetime.utcnow()
        }
        
        try:
            collection.insert_one(log_doc)
        except Exception as e:
            logger.error(f"Failed to log recommendation: {e}")


@router.get("", response_model=RecommendationResponse)
def get_recommendations(
    top_k: int = Query(10, ge=1, le=50, description="추천 논문 개수"),
    db_postgres: Session = Depends(get_db),
    db_mongo: Database = Depends(get_mongo_db),
    current_user: User = Depends(get_current_user)
):
    """
    사용자 맞춤 논문 추천.
    
    룰 베이스 추천 시스템을 사용하여 사용자에게 맞춤 논문을 추천합니다.
    
    점수 구성:
    - 관심사 매칭 (40%): 사용자 관심 카테고리와 논문 카테고리/키워드 매칭
    - 인기도 (20%): 조회수, 북마크 수
    - 최신성 (10%): 최근 업데이트된 논문 우선
    - 개인화 (30%): 사용자 활동 이력 기반
    """
    logger.info(f"Generating recommendations for user {current_user.id}")
    
    # 추천 생성
    recommender = RuleBasedRecommender()
    recommendations = recommender.recommend(
        user=current_user,
        db_postgres=db_postgres,
        db_mongo=db_mongo,
        top_k=top_k,
        candidate_limit=100
    )
    
    # 추천 로깅
    _log_recommendation(
        db=db_mongo,
        user_id=current_user.id,
        recommendations=recommendations
    )
    
    # 응답 생성
    recommendation_items = []
    for rec in recommendations:
        paper = rec["paper"]
        serialize_object_id(paper)
        
        item = RecommendationItem(
            paper_id=rec["paper_id"],
            title=paper.get("title", ""),
            abstract=paper.get("abstract"),
            authors=paper.get("authors"),
            categories=paper.get("categories", []),
            keywords=paper.get("keywords", []),
            difficulty_level=paper.get("difficulty_level"),
            view_count=paper.get("view_count", 0),
            bookmark_count=paper.get("bookmark_count", 0),
            update_date=paper.get("update_date"),
            total_score=rec["total_score"],
            breakdown=ScoreBreakdown(**rec["breakdown"]),
            reasons=rec["reasons"]
        )
        recommendation_items.append(item)
    
    return RecommendationResponse(
        user_id=current_user.id,
        recommendation_type="rule_based",
        recommendations=recommendation_items,
        total_count=len(recommendation_items),
        timestamp=datetime.utcnow().isoformat()
    )
