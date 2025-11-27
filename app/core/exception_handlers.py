"""
예외 처리 유틸리티.

공통 exception handler 로직을 제공합니다.
"""

import logging
from typing import Tuple
from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AppException,
    DatabaseException,
    ResourceNotFoundException,
    ValidationException,
    BusinessLogicException,
    UnauthorizedException,
    ForbiddenException,
    DuplicateResourceException,
)

logger = logging.getLogger(__name__)


def create_error_response(
    request: Request,
    exc: Exception,
    status_code: int,
    error_type: str,
    log_level: str = "warning",
) -> JSONResponse:
    """
    표준화된 에러 응답을 생성합니다.

    Args:
        request: FastAPI Request 객체
        exc: 발생한 예외
        status_code: HTTP 상태 코드
        error_type: 에러 타입
        log_level: 로그 레벨 ("info", "warning", "error")

    Returns:
        JSONResponse: 표준화된 에러 응답
    """
    error_message = str(exc)

    # 로깅
    if log_level == "error":
        logger.error(
            f"{error_type} at {request.url.path}: {error_message}", exc_info=True
        )
    elif log_level == "warning":
        logger.warning(f"{error_type} at {request.url.path}: {error_message}")
    else:
        logger.info(f"{error_type} at {request.url.path}: {error_message}")

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": error_message,
            "error_type": error_type,
            "path": str(request.url.path),
        },
    )


# 예외 타입별 상태 코드 및 에러 타입 매핑
EXCEPTION_CONFIG = {
    DatabaseException: (500, "database_error", "error"),
    ResourceNotFoundException: (404, "resource_not_found", "warning"),
    ValidationException: (400, "validation_error", "warning"),
    DuplicateResourceException: (409, "duplicate_resource", "warning"),
    BusinessLogicException: (400, "business_logic_error", "warning"),
    UnauthorizedException: (401, "unauthorized", "warning"),
    ForbiddenException: (403, "forbidden", "warning"),
    AppException: (400, "application_error", "warning"),
}


def get_exception_config(exc: Exception) -> Tuple[int, str, str]:
    """
    예외 타입에 따른 설정을 반환합니다.

    Returns:
        Tuple[int, str, str]: (status_code, error_type, log_level)
    """
    for exc_class, config in EXCEPTION_CONFIG.items():
        if isinstance(exc, exc_class):
            return config

    # 기본값
    return (500, "internal_server_error", "error")
