"""
사용자 활동 로그 관련 API 라우터.
"""

from fastapi import APIRouter, Query, Depends
from pymongo.database import Database

from app.db.mongodb import get_mongo_db
from app.schemas.activity import UserActivityListResponse, UserActivityOut
from app.utils.mongodb import serialize_object_id

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
    
    Args:
        user_id: 특정 사용자의 활동만 조회
        activity_type: 특정 활동 타입만 조회 (view, bookmark, search 등)
        doi: 특정 논문에 대한 활동만 조회 (arXiv ID)
        limit: 조회할 기록 수 (기본 100, 최대 1000)
        db: MongoDB Database
    
    Returns:
        UserActivityListResponse: 활동 로그 목록
    
    Example:
        GET /activities?user_id=123&limit=20
        GET /activities?activity_type=view&limit=50
        GET /activities?doi=0704.0775
    """
    collection = db["user_activities"]
    
    query = {}
    if user_id is not None:
        query["user_id"] = user_id
    if activity_type:
        query["activity_type"] = activity_type
    if doi:
        # doi는 이제 arXiv ID 문자열이므로 직접 사용
        query["doi"] = doi
    
    total = collection.count_documents(query)
    
    cursor = collection.find(query).sort("timestamp", -1).limit(limit)
    
    items = []
    for doc in cursor:
        serialize_object_id(doc)
        doc["id"] = doc.pop("_id")
        # doi는 문자열이므로 변환 불필요
        
        # metadata가 없으면 None으로 설정
        if "metadata" not in doc:
            doc["metadata"] = None
        
        items.append(UserActivityOut(**doc))
    
    return UserActivityListResponse(total=total, items=items)
