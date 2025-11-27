"""
추천 시스템 API 엔드포인트.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pymongo.database import Database

from app.db.postgres import get_db
from app.db.mongodb import get_mongo_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.recommendation import RecommendationResponse
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


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
    service = RecommendationService(db_mongo)
    result = service.get_recommendations(
        user=current_user,
        db_postgres=db_postgres,
        top_k=top_k
    )
    
    return RecommendationResponse(**result)
