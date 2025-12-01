"""
추천 시스템 API 엔드포인트.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pymongo.database import Database

from app.db.postgres import get_db
from app.db.mongodb import get_mongo_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.recommendation import RecommendationResponse, RecommendationLogListResponse
from app.schemas.recommendation_interaction import (
    RecommendationInteractionCreate,
    RecommendationInteraction,
    ClickResponse,
)
from app.services.recommendation_service import RecommendationService
from bson import ObjectId

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=RecommendationResponse)
def get_recommendations(
    top_k: int = Query(10, ge=1, le=50, description="추천 논문 개수"),
    db_postgres: Session = Depends(get_db),
    db_mongo: Database = Depends(get_mongo_db),
    current_user: User = Depends(get_current_user),
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
        user=current_user, db_postgres=db_postgres, top_k=top_k
    )

    return RecommendationResponse(**result)


@router.get("/logs", response_model=RecommendationLogListResponse)
def get_all_recommendation_logs(
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    db_mongo: Database = Depends(get_mongo_db),
):
    """
    전체 추천 로그 조회 (관리자용).

    모든 사용자의 추천 이력을 페이지네이션하여 조회합니다.
    최신 추천 순으로 정렬됩니다.
    """
    service = RecommendationService(db_mongo)
    result = service.get_all_recommendation_logs(page=page, page_size=page_size)
    return RecommendationLogListResponse(**result)


@router.get("/logs/users/{user_id}", response_model=RecommendationLogListResponse)
def get_user_recommendation_logs(
    user_id: int,
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    db_mongo: Database = Depends(get_mongo_db),
):
    """
    특정 사용자의 추천 로그 조회.

    특정 사용자 ID로 필터링된 추천 이력을 페이지네이션하여 조회합니다.
    최신 추천 순으로 정렬됩니다.
    """
    service = RecommendationService(db_mongo)
    result = service.get_user_recommendation_logs(
        user_id=user_id, page=page, page_size=page_size
    )
    return RecommendationLogListResponse(**result)


@router.post("/{recommendation_id}/click", response_model=ClickResponse)
def record_recommendation_click(
    recommendation_id: str,
    db_mongo: Database = Depends(get_mongo_db),
    current_user: User = Depends(get_current_user),
):
    """
    추천된 논문 클릭 기록.
    
    paper_recommendations 컬렉션의 was_clicked를 true로 업데이트하고
    clicked_at 시각을 기록합니다.
    """
    service = RecommendationService(db_mongo)
    result = service.record_click(recommendation_id, current_user.id)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=f"추천 ID {recommendation_id}를 찾을 수 없습니다")
    
    return ClickResponse(**result)


@router.post("/{recommendation_id}/interactions", response_model=RecommendationInteraction)
def record_recommendation_interaction(
    recommendation_id: str,
    interaction_data: RecommendationInteractionCreate,
    db_mongo: Database = Depends(get_mongo_db),
    current_user: User = Depends(get_current_user),
):
    """
    추천 논문 상호작용 데이터 저장.
    
    체류 시간, 스크롤 깊이, 북마크 상호작용 데이터를
    recommendation_interactions 컬렉션에 저장합니다.
    """
    # recommendation_id로부터 user_id와 paper_id 조회
    recommendations_coll = db_mongo["paper_recommendations"]
    rec = recommendations_coll.find_one({"_id": ObjectId(recommendation_id)})
    
    if not rec:
        raise HTTPException(status_code=404, detail=f"추천 ID {recommendation_id}를 찾을 수 없습니다")
    
    if rec["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="이 추천에 접근할 권한이 없습니다")
    
    service = RecommendationService(db_mongo)
    interaction_dict = interaction_data.model_dump(exclude_unset=True, exclude={"recommendation_id"})
    
    result = service.record_interaction(
        recommendation_id=recommendation_id,
        user_id=rec["user_id"],
        paper_id=rec["paper_id"],
        interaction_data=interaction_dict,
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="상호작용 데이터 저장에 실패했습니다")
    
    return RecommendationInteraction(**result)


