"""
사용자 관심사(UserInterest) 관련 Pydantic 스키마.

PostgreSQL user_interests 테이블과 연동하며,
API 요청/응답 모델을 정의합니다.
"""

from pydantic import BaseModel, Field


class InterestAddPayload(BaseModel):
    """
    관심 카테고리 추가 요청 모델.
    """
    category_codes: list[str] = Field(min_length=1)


class InterestItem(BaseModel):
    """
    관심 카테고리 항목 모델.
    """
    code: str
    name_ko: str | None = None
    name_en: str | None = None


class InterestList(BaseModel):
    """
    관심 카테고리 목록 응답 모델.
    """
    items: list[InterestItem]


class InterestRemovalResult(BaseModel):
    """
    관심 카테고리 삭제 결과 응답 모델.
    """
    removed: int
    not_found: list[str]
    remaining: InterestList
