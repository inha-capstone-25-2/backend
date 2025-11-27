"""
에러 응답 스키마.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """상세 에러 정보."""

    field: Optional[str] = None
    message: str


class ErrorResponse(BaseModel):
    """
    표준화된 에러 응답 포맷.

    모든 API 에러는 이 포맷을 따릅니다.
    """

    success: bool = False
    error: str
    error_type: str
    path: str
    details: Optional[list[ErrorDetail] | Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "Resource not found",
                "error_type": "resource_not_found",
                "path": "/api/papers/123",
                "details": None,
            }
        }
