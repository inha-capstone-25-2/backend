"""
추천 이벤트 관련 Pydantic 스키마.

recommendation_events 컬렉션에 저장되는 사용자 행동 이벤트 스키마.
RL 모델의 reward 계산에 사용됩니다.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ActivityType(str, Enum):
    """이벤트 유형"""
    SESSION_CONTEXT = "session_context"  # 세션 컨텍스트 (RL 메타데이터)
    EXPOSE = "expose"  # 추천 노출
    CLICK = "click"  # 클릭
    BOOKMARK = "bookmark"  # 북마크
    DETAIL_VIEW = "detail_view"  # 상세 페이지 조회
    CLOSE = "close"  # 페이지 닫기


class EventMetadata(BaseModel):
    """이벤트 메타데이터"""
    # expose 시
    candidates: Optional[List[str]] = Field(None, description="전체 추천 후보군 (paper_id 리스트)")
    position: Optional[int] = Field(None, ge=0, description="추천 리스트 내 위치 (0-based)")
    
    # detail_view, close 시
    dwell_time_ms: Optional[int] = Field(None, ge=0, description="체류 시간 (밀리초)")
    
    class Config:
        extra = "allow"  # 추가 필드 허용


class RecommendationEventCreate(BaseModel):
    """추천 이벤트 생성 요청"""
    user_id: int = Field(..., description="사용자 ID")
    paper_id: str = Field(..., description="논문 ID")
    activity_type: ActivityType = Field(..., description="활동 유형")
    session_id: str = Field(..., description="세션 ID")
    metadata: Optional[EventMetadata] = Field(None, description="이벤트 메타데이터")


class RecommendationEvent(BaseModel):
    """추천 이벤트 응답"""
    id: str = Field(..., description="이벤트 ID")
    user_id: int = Field(..., description="사용자 ID")
    paper_id: str = Field(..., description="논문 ID")
    activity_type: ActivityType = Field(..., description="활동 유형")
    timestamp: str = Field(..., description="이벤트 발생 시각 (ISO format)")
    session_id: str = Field(..., description="세션 ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="이벤트 메타데이터")


class EventListResponse(BaseModel):
    """이벤트 목록 조회 응답"""
    total: int = Field(..., description="전체 이벤트 개수")
    page: int = Field(..., description="현재 페이지")
    page_size: int = Field(..., description="페이지 크기")
    items: List[RecommendationEvent] = Field(..., description="이벤트 목록")
