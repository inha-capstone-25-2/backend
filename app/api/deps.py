from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from app.db.postgres import get_db
from app.models.user import User
from app.core.settings import settings
from cachetools import TTLCache

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# 사용자 정보 캐시 (TTL 5분, 최대 1024개)
# Key: (username, token_version)
user_cache = TTLCache(maxsize=1024, ttl=300)

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        username: str | None = payload.get("sub")   # sub은 username
        token_ver = payload.get("ver", 0)           # 토큰 버전(없으면 0으로 간주)
        if username is None:
            raise credentials_error
    except JWTError:
        raise credentials_error

    # 1. 캐시 확인
    cache_key = (username, token_ver)
    if cache_key in user_cache:
        return user_cache[cache_key]

    # 2. DB 조회
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise credentials_error

    # 토큰 버전 불일치 시(로그아웃 이후의 오래된 토큰) 인증 실패
    if int(token_ver) != int(getattr(user, "token_version", 0)):
        raise credentials_error

    # 3. 캐시 저장 (세션에서 분리하여 저장)
    # 주의: 분리된 객체는 지연 로딩된 관계(interests 등)에 접근 시 에러 발생 가능
    # 현재 로직상 user.id 등 기본 필드만 주로 사용하므로 안전
    db.expunge(user)
    user_cache[cache_key] = user

    return user