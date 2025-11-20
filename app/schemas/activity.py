"""
사용자 활동 로그 관련 Pydantic 스키마.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class ActivityType(str, Enum):
    """활동 타입"""
    VIEW = "view"
    BOOKMARK = "bookmark"
    UNBOOKMARK = "unbookmark"
    SEARCH = "search"
    CLICK = "click"


class ActivityMetadata(BaseModel):
    """활동 메타데이터 (선택적 필드들)"""
    session_id: Optional[str] = None
    duration_seconds: Optional[int] = None
    search_query: Optional[str] = None
    categories: Optional[List[str]] = None
    result_count: Optional[int] = None
    from_recommendation: Optional[bool] = None


class UserActivityOut(BaseModel):
    """활동 로그 응답"""
    id: str
    user_id: int
    paper_id: Optional[str] = None
    activity_type: str
    metadata: Dict[str, Any]
    timestamp: datetime


class UserActivityListResponse(BaseModel):
    """활동 로그 목록 응답"""
    total: int
    items: List[UserActivityOut]
