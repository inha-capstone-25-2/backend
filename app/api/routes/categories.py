"""카테고리 API 라우터 모듈.

카테고리 관련 API 엔드포인트를 정의합니다.
현재 이 라우터는 빈 상태입니다.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/categories", tags=["categories"])

# 카테고리 시드는 초기 데이터 설정 시에만 필요하므로
# run_seed.py 또는 initdb 스크립트를 통해 수행합니다.
