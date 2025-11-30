"""
추천 이벤트 API 엔드포인트.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from pymongo.database import Database

from app.db.mongodb import get_mongo_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.recommendation_event import (
    RecommendationEventCreate,
    RecommendationEvent,
    EventListResponse,
    ActivityType,
)
from app.repositories.recommendation_repository import RecommendationRepository
from app.utils.mongodb import serialize_object_id

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=RecommendationEvent, status_code=201)
def create_event(
    event_data: RecommendationEventCreate,
    db_mongo: Database = Depends(get_mongo_db),
    current_user: User = Depends(get_current_user),
):
    """
    추천 이벤트 로깅.
    
    사용자의 추천 관련 행동(expose, click, bookmark 등)을 기록합니다.
    RL 모델의 reward 계산에 사용됩니다.
    """
    repo = RecommendationRepository(db_mongo)
    
    # 메타데이터 변환
    metadata_dict = event_data.metadata.model_dump(exclude_none=True) if event_data.metadata else {}
    
    # 이벤트 로깅
    event_id = repo.log_event(
        user_id=event_data.user_id,
        paper_id=event_data.paper_id,
        activity_type=event_data.activity_type.value,
        session_id=event_data.session_id,
        metadata=metadata_dict,
    )
    
    # 저장된 문서 조회
    if event_id:
        event_doc = db_mongo["recommendation_events"].find_one({"_id": event_id})
        if event_doc:
            serialize_object_id(event_doc)
            event_doc["id"] = event_doc.pop("_id")
            if hasattr(event_doc.get("timestamp"), "isoformat"):
                event_doc["timestamp"] = event_doc["timestamp"].isoformat()
            
            return RecommendationEvent(**event_doc)
    
    raise HTTPException(status_code=500, detail="Failed to create event")


@router.get("/session/{session_id}", response_model=EventListResponse)
def get_session_events(
    session_id: str,
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(50, ge=1, le=100, description="페이지 크기"),
    db_mongo: Database = Depends(get_mongo_db),
    current_user: User = Depends(get_current_user),
):
    """
    세션별 이벤트 조회.
    
    동일 세션 내의 모든 이벤트를 시간순으로 조회합니다.
    """
    repo = RecommendationRepository(db_mongo)
    total, items = repo.get_events_by_session(session_id, page, page_size)
    
    # 변환
    formatted_items = []
    for item in items:
        serialize_object_id(item)
        item["id"] = item.pop("_id")
        if hasattr(item.get("timestamp"), "isoformat"):
            item["timestamp"] = item["timestamp"].isoformat()
        formatted_items.append(item)
    
    return EventListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=formatted_items,
    )


@router.get("/users/{user_id}", response_model=EventListResponse)
def get_user_events(
    user_id: int,
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(50, ge=1, le=100, description="페이지 크기"),
    db_mongo: Database = Depends(get_mongo_db),
    current_user: User = Depends(get_current_user),
):
    """
    사용자별 이벤트 조회.
    
    특정 사용자의 모든 이벤트를 최신순으로 조회합니다.
    """
    repo = RecommendationRepository(db_mongo)
    total, items = repo.get_events_by_user(user_id, page, page_size)
    
    # 변환
    formatted_items = []
    for item in items:
        serialize_object_id(item)
        item["id"] = item.pop("_id")
        if hasattr(item.get("timestamp"), "isoformat"):
            item["timestamp"] = item["timestamp"].isoformat()
        formatted_items.append(item)
    
    return EventListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=formatted_items,
    )
