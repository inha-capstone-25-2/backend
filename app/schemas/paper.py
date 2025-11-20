"""
논문(Paper) 관련 Pydantic 스키마.

MongoDB arxiv_papers 컬렉션의 문서를 표현하고,
API 요청/응답 모델을 정의합니다.
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class Paper(BaseModel):
    """
    논문 응답 모델.
    
    MongoDB arxiv_papers 컬렉션의 문서를 표현합니다.
    """
    _id: str
    id: Optional[str] = None
    title: Optional[str] = None
    abstract: Optional[str] = None
    authors: Optional[str] = None
    categories: Optional[List[str]] = None
    update_date: Optional[str] = None


class PaperSearchResponse(BaseModel):
    """
    논문 검색 결과 응답 모델.
    
    페이지네이션 정보와 검색 결과를 포함합니다.
    """
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool
    items: List[Paper]


class SearchHistoryFilters(BaseModel):
    """검색 필터 정보"""
    categories: List[str] = []


class SearchHistoryItem(BaseModel):
    """검색 기록 항목"""
    id: str  # _id를 id로 변환
    user_id: int
    query: str
    filters: SearchHistoryFilters
    result_count: int
    searched_at: datetime


class SearchHistoryResponse(BaseModel):
    """검색 기록 조회 응답"""
    total: int
    items: List[SearchHistoryItem]
