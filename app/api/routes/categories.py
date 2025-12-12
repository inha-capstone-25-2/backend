"""카테고리 API 라우터 모듈.

카테고리 관련 API 엔드포인트를 정의합니다.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/categories", tags=["categories"])
