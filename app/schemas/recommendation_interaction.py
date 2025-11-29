"""
추천 상호작용 데이터 관련 Pydantic 스키마.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class RecommendationClickRequest(BaseModel):
    """클릭 기록 요청"""
    
    recommendation_id: str = Field(..., description="추천 ID")


class RecommendationInteractionCreate(BaseModel):
    """상호작용 데이터 생성 요청"""
    
    recommendation_id: str = Field(..., description="추천 ID")
    dwell_time_seconds: Optional[int] = Field(None, description="체류 시간 (초)")
    scroll_depth_percent: Optional[int] = Field(None, ge=0, le=100, description="스크롤 깊이 (%)")
    read_abstract: Optional[bool] = Field(None, description="초록 읽음 여부")
    expanded_sections: Optional[List[str]] = Field(None, description="확장한 섹션들")
    bookmarked: Optional[bool] = Field(None, description="북마크 여부")
    downloaded_pdf: Optional[bool] = Field(None, description="PDF 다운로드 여부")
    copied_citation: Optional[bool] = Field(None, description="인용 정보 복사 여부")
    shared: Optional[bool] = Field(None, description="공유 여부")
    device_type: Optional[str] = Field(None, description="디바이스 타입 (desktop, mobile, tablet)")


class RecommendationInteraction(BaseModel):
    """상호작용 데이터 응답"""
    
    id: str = Field(..., description="상호작용 ID")
    recommendation_id: str = Field(..., description="추천 ID")
    user_id: int = Field(..., description="사용자 ID")
    paper_id: str = Field(..., description="논문 ID")
    dwell_time_seconds: Optional[int] = Field(None, description="체류 시간 (초)")
    scroll_depth_percent: Optional[int] = Field(None, description="스크롤 깊이 (%)")
    read_abstract: Optional[bool] = Field(None, description="초록 읽음 여부")
    expanded_sections: Optional[List[str]] = Field(None, description="확장한 섹션들")
    bookmarked: Optional[bool] = Field(None, description="북마크 여부")
    downloaded_pdf: Optional[bool] = Field(None, description="PDF 다운로드 여부")
    copied_citation: Optional[bool] = Field(None, description="인용 정보 복사 여부")
    shared: Optional[bool] = Field(None, description="공유 여부")
    device_type: Optional[str] = Field(None, description="디바이스 타입")
    created_at: str = Field(..., description="생성 시각 (ISO format)")
    updated_at: str = Field(..., description="수정 시각 (ISO format)")


class ClickResponse(BaseModel):
    """클릭 기록 응답"""
    
    success: bool = Field(..., description="성공 여부")
    clicked_at: str = Field(..., description="클릭 시각 (ISO format)")
