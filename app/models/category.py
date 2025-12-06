"""카테고리 모델.

PostgreSQL categories, category_names 테이블에 대응하는 SQLAlchemy 모델을 정의합니다.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    String,
    Integer,
    SmallInteger,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres import Base


class Category(Base):
    """카테고리 모델.

    Attributes:
        id: 카테고리 고유 ID.
        code: 카테고리 코드 (예: cs.AI).
        parent_id: 부모 카테고리 ID.
        depth: 카테고리 깊이.
        sort_order: 정렬 순서.
        created_at: 생성 시각.
        parent: 부모 카테고리.
        children: 자식 카테고리 목록.
        names: 다국어 카테고리 이름 목록.
        interested_users: 이 카테고리를 관심으로 등록한 사용자 목록.
    """

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    depth: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    parent: Mapped["Category"] = relationship(
        "Category",
        remote_side="Category.id",
        back_populates="children",
    )
    children: Mapped[List["Category"]] = relationship(
        "Category",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    names: Mapped[List["CategoryName"]] = relationship(
        "CategoryName",
        back_populates="category",
        cascade="all, delete-orphan",
    )

    # 이 카테고리를 관심으로 등록한 사용자 관계
    interested_users: Mapped[List["UserInterest"]] = relationship(
        "UserInterest",
        back_populates="category",
        cascade="all, delete-orphan",
    )


class CategoryName(Base):
    __tablename__ = "category_names"
    __table_args__ = (
        UniqueConstraint("category_id", "locale", name="uq_category_locale"),
    )

    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
    )
    locale: Mapped[str] = mapped_column(String(5), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    category: Mapped[Category] = relationship(
        "Category",
        back_populates="names",
    )
