"""사용자 모델.

PostgreSQL users 테이블에 대응하는 SQLAlchemy 모델을 정의합니다.
"""

from sqlalchemy import Column, Integer, String, DateTime, func, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.db.postgres import Base


class User(Base):
    """사용자 모델.

    Attributes:
        id: 사용자 고유 ID.
        email: 이메일 주소.
        username: 사용자명 (로그인 ID).
        name: 사용자 이름.
        hashed_password: 해시된 비밀번호.
        token_version: JWT 토큰 버전 (로그아웃 처리용).
        is_active: 계정 활성화 상태.
        created_at: 계정 생성 시각.
        updated_at: 계정 수정 시각.
        interests: 사용자 관심 카테고리 목록.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # 이름
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    token_version: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    interests: Mapped[list["UserInterest"]] = relationship(
        "UserInterest",
        back_populates="user",
        cascade="all, delete-orphan",
    )
