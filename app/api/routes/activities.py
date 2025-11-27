"""
사용자 활동 로그 관련 API 라우터.
"""

from fastapi import APIRouter, Query, Depends
from pymongo.database import Database

from app.db.mongodb import get_mongo_db
from app.schemas.activity import UserActivityListResponse, UserActivityOut
from app.services.activity_service import ActivityService

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get("", response_model=UserActivityListResponse)
def get_activities(
    user_id: int | None = Query(None, description="사용자 ID로 필터링"),
    activity_type: str | None = Query(None, description="활동 타입으로 필터링 (view, bookmark, search 등)"),
    doi: str | None = Query(None, description="논문 DOI로 필터링"),
    limit: int = Query(100, ge=1, le=1000, description="조회할 기록 수"),
    db: Database = Depends(get_mongo_db),
):
    """
    활동 로그 조회 (인증 불필요).
    
    필터 옵션으로 특정 사용자, 활동 타입, 논문의 활동만 조회 가능합니다.
    최신순으로 정렬되어 반환됩니다.
    """
    service = ActivityService(db)
    result = service.get_activities(user_id, activity_type, doi, limit)
    
    items = [UserActivityOut(**doc) for doc in result["items"]]
    
    return UserActivityListResponse(total=result["total"], items=items)
