"""
추천 시스템 관련 Pydantic 스키마.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class ScoreBreakdown(BaseModel):
    """점수 분해 정보"""

    interest_score: float = Field(..., description="관심사 매칭 점수")
    popularity_score: float = Field(..., description="인기도 점수")
    recency_score: float = Field(..., description="최신성 점수")
    personalization_score: float = Field(..., description="개인화 점수")


class RecommendationItem(BaseModel):
    """개별 추천 아이템"""

    paper_id: str = Field(..., description="논문 ID")
    title: str = Field(..., description="논문 제목")
    abstract: Optional[str] = Field(None, description="초록")
    authors: Optional[str] = Field(None, description="저자")
    categories: List[str] = Field(
        default_factory=list, description="카테고리 코드 리스트"
    )
    keywords: List[str] = Field(default_factory=list, description="키워드 리스트")
    difficulty_level: Optional[str] = Field(None, description="난이도 레벨")
    view_count: int = Field(0, description="조회 수")
    bookmark_count: int = Field(0, description="북마크 수")
    update_date: Optional[str] = Field(None, description="최종 수정일")

    total_score: float = Field(..., description="총점")
    breakdown: ScoreBreakdown = Field(..., description="점수 분해")
    reasons: List[str] = Field(default_factory=list, description="추천 이유")


class RecommendationResponse(BaseModel):
    """추천 결과 응답"""

    user_id: int = Field(..., description="사용자 ID")
    recommendation_type: str = Field("rule_based", description="추천 타입")
    recommendations: List[RecommendationItem] = Field(
        ..., description="추천 논문 리스트"
    )
    total_count: int = Field(..., description="추천된 논문 수")
    timestamp: str = Field(..., description="추천 생성 시각 (ISO format)")


class RecommendationLog(BaseModel):
    """추천 로그 항목 (MongoDB paper_recommendations 컬렉션)"""

    id: str = Field(..., description="로그 ID")
    user_id: int = Field(..., description="사용자 ID")
    paper_id: str = Field(..., description="논문 ID")
    recommendation_type: str = Field(..., description="추천 타입")
    score: float = Field(..., description="추천 점수")
    features: Dict[str, float] = Field(..., description="점수 분해 정보")
    context: Dict[str, Any] = Field(..., description="추가 컨텍스트")
    was_clicked: bool = Field(..., description="클릭 여부")
    recommended_at: str = Field(..., description="추천된 시각 (ISO format)")


class RecommendationLogListResponse(BaseModel):
    """추천 로그 목록 조회 응답"""

    total: int = Field(..., description="전체 로그 개수")
    page: int = Field(..., description="현재 페이지")
    page_size: int = Field(..., description="페이지 크기")
    items: List[RecommendationLog] = Field(..., description="추천 로그 목록")
