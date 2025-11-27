"""
논문(Paper) 관련 Pydantic 스키마.

MongoDB arxiv_papers 컬렉션의 문서를 표현하고,
API 요청/응답 모델을 정의합니다.
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class PaperListItem(BaseModel):
    """
    논문 리스트 아이템 모델 (검색 결과용).

    abstract를 제외하여 네트워크 전송량을 최소화합니다.
    MongoDB _id는 id 필드로 변환되어 반환됩니다.
    """

    id: str
    title: Optional[str] = None
    authors: Optional[str] = None
    categories: Optional[List[str]] = None
    update_date: Optional[str] = None
    view_count: Optional[int] = 0


class Paper(BaseModel):
    """
    논문 상세 응답 모델.

    MongoDB papers 컬렉션의 문서를 표현합니다.
    상세 조회 시 사용되며 모든 필드를 포함합니다.
    MongoDB _id는 id 필드로 변환되어 반환됩니다.
    """

    id: str
    title: Optional[str] = None
    abstract: Optional[str] = None
    authors: Optional[str] = None
    categories: Optional[List[str]] = None
    update_date: Optional[str] = None
    view_count: Optional[int] = 0


class PaperSearchResponse(BaseModel):
    """
    논문 검색 결과 응답 모델.

    페이지네이션 정보와 검색 결과를 포함합니다.
    abstract를 제외한 PaperListItem을 사용하여 응답 크기를 최소화합니다.
    """

    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool
    is_approximate: bool = False  # total이 근사치인지 여부
    items: List[PaperListItem]


class SearchHistoryFilters(BaseModel):
    """검색 필터 정보"""

    categories: List[str] = []


class SearchHistoryItem(BaseModel):
    """검색 기록 항목"""

    id: str  # _id를 id로 변환
    query: str
    searched_at: datetime
    user_id: Optional[int] = None
    filters: Optional[SearchHistoryFilters] = None
    result_count: Optional[int] = None


class SearchHistoryResponse(BaseModel):
    """검색 기록 조회 응답"""

    total: int
    items: List[SearchHistoryItem]
