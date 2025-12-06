"""보안 유틸리티 모듈.

비밀번호 해싱, 검증, JWT 토큰 생성 등의 보안 관련 기능을 제공합니다.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Dict
from passlib.context import CryptContext
from jose import jwt
from app.core.settings import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """비밀번호를 bcrypt 해시로 변환한다.

    Args:
        password: 해시할 평문 비밀번호.

    Returns:
        bcrypt로 해시된 비밀번호 문자열.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """평문 비밀번호와 해시된 비밀번호를 비교 검증한다.

    Args:
        plain_password: 검증할 평문 비밀번호.
        hashed_password: 저장된 해시 비밀번호.

    Returns:
        비밀번호가 일치하면 True, 그렇지 않으면 False.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """JWT 액세스 토큰을 생성한다.

    Args:
        data: 토큰에 인코딩할 페이로드 데이터.
        expires_delta: 토큰 만료 시간. 미지정시 설정값 사용.

    Returns:
        인코딩된 JWT 토큰 문자열.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)
