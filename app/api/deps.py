"""FastAPI 의존성 주입 모듈.

API 엔드포인트에서 사용하는 공통 의존성을 정의합니다.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from app.db.postgres import get_db
from app.models.user import User
from app.core.settings import settings
from app.core.constants import USER_CACHE_TTL_SECONDS, USER_CACHE_MAX_SIZE
from cachetools import TTLCache

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

user_cache = TTLCache(maxsize=USER_CACHE_MAX_SIZE, ttl=USER_CACHE_TTL_SECONDS)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """현재 인증된 사용자를 반환한다.

    Args:
        token: JWT 액세스 토큰.
        db: 데이터베이스 세션.

    Returns:
        인증된 User 객체.

    Raises:
        HTTPException: 인증 실패 시 401 에러.
    """
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        username: str | None = payload.get("sub")
        token_ver = payload.get("ver", 0)
        if username is None:
            raise credentials_error
    except JWTError:
        raise credentials_error

    cache_key = (username, token_ver)
    if cache_key in user_cache:
        return user_cache[cache_key]

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise credentials_error

    if int(token_ver) != int(getattr(user, "token_version", 0)):
        raise credentials_error

    db.expunge(user)
    user_cache[cache_key] = user

    return user
