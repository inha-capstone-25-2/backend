"""
User Interest Repository.

PostgreSQL 기반 사용자 관심사 데이터 접근 레이어.
"""

import logging
from typing import List

from sqlalchemy.orm import Session, joinedload

from app.models.user_interest import UserInterest
from app.models.category import Category

logger = logging.getLogger(__name__)


class UserInterestRepository:
    """사용자 관심사 데이터 접근 레이어."""

    def __init__(self, db: Session):
        self.db = db

    def find_categories_by_codes(self, codes: List[str]) -> List[Category]:
        """
        카테고리 코드 리스트로 카테고리 조회.

        Args:
            codes: 카테고리 코드 리스트

        Returns:
            Category 객체 리스트
        """
        return self.db.query(Category).filter(Category.code.in_(codes)).all()

    def find_user_interests_by_user_and_categories(
        self, user_id: int, category_ids: List[int]
    ) -> List[UserInterest]:
        """
        사용자 ID와 카테고리 ID 리스트로 기존 관심사 조회.

        Args:
            user_id: 사용자 ID
            category_ids: 카테고리 ID 리스트

        Returns:
            UserInterest 객체 리스트
        """
        return (
            self.db.query(UserInterest)
            .filter(
                UserInterest.user_id == user_id,
                UserInterest.category_id.in_(category_ids),
            )
            .all()
        )

    def create_user_interest(self, user_id: int, category_id: int) -> UserInterest:
        """
        새로운 사용자 관심사 생성.

        Args:
            user_id: 사용자 ID
            category_id: 카테고리 ID

        Returns:
            생성된 UserInterest 객체
        """
        user_interest = UserInterest(user_id=user_id, category_id=category_id)
        self.db.add(user_interest)
        return user_interest

    def list_user_interests(self, user_id: int) -> List[Category]:
        """
        사용자의 모든 관심사 조회 (Category join 포함).

        Args:
            user_id: 사용자 ID

        Returns:
            Category 객체 리스트 (CategoryName 관계 포함)
        """
        query = (
            self.db.query(Category)
            .join(UserInterest, UserInterest.category_id == Category.id)
            .filter(UserInterest.user_id == user_id)
            .options(joinedload(Category.names))
            .order_by(Category.code.asc())
        )
        return query.all()

    def delete_user_interests(
        self, user_id: int, category_ids: List[int]
    ) -> List[UserInterest]:
        """
        사용자 관심사 삭제.

        Args:
            user_id: 사용자 ID
            category_ids: 삭제할 카테고리 ID 리스트

        Returns:
            삭제된 UserInterest 객체 리스트
        """
        to_delete = (
            self.db.query(UserInterest)
            .filter(
                UserInterest.user_id == user_id,
                UserInterest.category_id.in_(category_ids),
            )
            .all()
        )

        for user_interest in to_delete:
            self.db.delete(user_interest)

        return to_delete
