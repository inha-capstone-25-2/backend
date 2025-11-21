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
    paper_id: str | None = Query(None, description="논문 ID로 필터링"),
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
        paper_id: 특정 논문에 대한 활동만 조회
        limit: 조회할 기록 수 (기본 100, 최대 1000)
        db: MongoDB Database
    
    Returns:
        UserActivityListResponse: 활동 로그 목록
    
    Example:
        GET /activities?user_id=123&limit=20
        GET /activities?activity_type=view&limit=50
        GET /activities?paper_id=507f1f77bcf86cd799439011
    """
    collection = db["user_activities"]
    
    query = {}
    if user_id is not None:
        query["user_id"] = user_id
    if activity_type:
        query["activity_type"] = activity_type
    if paper_id:
        from app.utils.mongodb import safe_object_id
        try:
            query["paper_id"] = safe_object_id(paper_id, "paper ID")
        except:
            # 유효하지 않은 paper_id면 빈 결과 반환
            return UserActivityListResponse(total=0, items=[])
    
    total = collection.count_documents(query)
    
    cursor = collection.find(query).sort("timestamp", -1).limit(limit)
    
    items = []
    for doc in cursor:
        serialize_object_id(doc)
        doc["id"] = doc.pop("_id")
        if "paper_id" in doc:
            doc["paper_id"] = str(doc["paper_id"])
        
        # metadata가 없으면 None으로 설정
        if "metadata" not in doc:
            doc["metadata"] = None
        
        items.append(UserActivityOut(**doc))
    
    return UserActivityListResponse(total=total, items=items)
