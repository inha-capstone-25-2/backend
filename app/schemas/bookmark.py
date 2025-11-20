"""
북마크(Bookmark) 관련 Pydantic 스키마.

MongoDB bookmarks 컬렉션의 문서를 표현하고,
API 요청/응답 모델을 정의합니다.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class BookmarkCreate(BaseModel):
    """
    북마크 생성 요청 모델.
    """
    paper_id: str = Field(..., description="MongoDB papers._id")
    notes: Optional[str] = None


class BookmarkOut(BaseModel):
    """
    북마크 응답 모델.
    """
    id: str
    user_id: int
    paper_id: str
    bookmarked_at: datetime
    notes: Optional[str] = None


class BookmarkUpdate(BaseModel):
    """
    북마크 수정 요청 모델.
    """
    notes: Optional[str] = None


class BookmarkListOut(BaseModel):
    """
    북마크 목록 응답 모델.
    """
    items: List[BookmarkOut]
