"""
User Interest Service.

사용자 관심사 비즈니스 로직 레이어.
"""

import logging
from typing import List, Dict

from sqlalchemy.orm import Session

from app.repositories.user_interest_repository import UserInterestRepository
from app.models.user import User
from app.schemas.user_interest import InterestItem, InterestList, InterestRemovalResult
from app.core.exceptions import ResourceNotFoundException, ValidationException

logger = logging.getLogger(__name__)


class UserInterestService:
    """사용자 관심사 비즈니스 로직 레이어."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = UserInterestRepository(db)

    def add_interests(
        self, user: User, category_codes: List[str]
    ) -> Dict[str, int]:
        """
        사용자 관심사 추가.

        Args:
            user: 사용자 객체
            category_codes: 추가할 카테고리 코드 리스트

        Returns:
            {"added": 추가된 개수, "skipped": 스킵된 개수}

        Raises:
            ValidationException: 빈 리스트인 경우
            ResourceNotFoundException: 존재하지 않는 카테고리인 경우
        """
        # 1. 중복 제거
        codes = list(dict.fromkeys(category_codes))

        # 2. 빈 리스트 검증
        if not codes:
            raise ValidationException("empty category_codes")

        # 3. 카테고리 존재 확인
        categories = self.repo.find_categories_by_codes(codes)
        found_codes = {c.code for c in categories}
        missing = [c for c in codes if c not in found_codes]

        if missing:
            raise ResourceNotFoundException(
                "Category", f"categories not found: {missing}"
            )

        # 4. 이미 존재하는 관심사 확인
        category_ids = [c.id for c in categories]
        existing = self.repo.find_user_interests_by_user_and_categories(
            user.id, category_ids
        )
        existing_ids = {e.category_id for e in existing}

        # 5. 새로운 관심사만 추가
        added_count = 0
        for category in categories:
            if category.id not in existing_ids:
                self.repo.create_user_interest(user.id, category.id)
                added_count += 1

        # 6. 커밋
        self.db.commit()

        return {
            "added": added_count,
            "skipped": len(existing_ids)
        }

    def list_interests(self, user: User) -> InterestList:
        """
        사용자 관심사 목록 조회.

        Args:
            user: 사용자 객체

        Returns:
            InterestList 스키마
        """
        categories = self.repo.list_user_interests(user.id)

        items: List[InterestItem] = []
        for category in categories:
            name_ko = next(
                (n.name for n in category.names if n.locale == "ko"), None
            )
            name_en = next(
                (n.name for n in category.names if n.locale == "en"), None
            )
            items.append(
                InterestItem(
                    code=category.code,
                    name_ko=name_ko,
                    name_en=name_en
                )
            )

        return InterestList(items=items)

    def remove_interests(
        self, user: User, codes: List[str]
    ) -> InterestRemovalResult:
        """
        사용자 관심사 삭제.

        Args:
            user: 사용자 객체
            codes: 삭제할 카테고리 코드 리스트

        Returns:
            InterestRemovalResult 스키마

        Raises:
            ValidationException: 빈 리스트인 경우
        """
        # 1. 중복 제거
        target_codes = list(dict.fromkeys(codes))

        # 2. 빈 리스트 검증
        if not target_codes:
            raise ValidationException("empty codes")

        # 3. 카테고리 조회
        categories = self.repo.find_categories_by_codes(target_codes)
        found_map = {c.code: c for c in categories}
        missing = [c for c in target_codes if c not in found_map]

        # 4. 삭제 수행
        category_ids = [c.id for c in found_map.values()]
        deleted = self.repo.delete_user_interests(user.id, category_ids)

        # 5. 커밋
        self.db.commit()

        # 6. 남은 관심사 조회
        remaining_categories = self.repo.list_user_interests(user.id)
        remaining_items = []
        for category in remaining_categories:
            name_ko = next(
                (n.name for n in category.names if n.locale == "ko"), None
            )
            name_en = next(
                (n.name for n in category.names if n.locale == "en"), None
            )
            remaining_items.append(
                InterestItem(
                    code=category.code,
                    name_ko=name_ko,
                    name_en=name_en
                )
            )

        return InterestRemovalResult(
            removed=len(deleted),
            not_found=missing,
            remaining=InterestList(items=remaining_items),
        )
