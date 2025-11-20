"""
Dev 환경용 Mock 사용자 관심사 데이터 생성 스크립트.

각 사용자에게 2~5개의 랜덤 카테고리를 관심사로 할당합니다.
"""
from __future__ import annotations
import logging
import random
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.category import Category
from app.models.user_interest import UserInterest
from app.db.postgres import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_user_interests(db: Session, min_interests: int = 2, max_interests: int = 5) -> int:
    """
    모든 사용자에게 랜덤 카테고리를 관심사로 할당합니다.
    
    Args:
        db: SQLAlchemy Session
        min_interests: 최소 관심사 개수
        max_interests: 최대 관심사 개수
    
    Returns:
        생성된 UserInterest 개수
    """
    users = db.query(User).all()
    categories = db.query(Category).all()

    if not users:
        logger.warning("⚠️ No users found. Please run users_seed.py first.")
        return 0

    if not categories:
        logger.warning("⚠️ No categories found. Please run categories_seed.py first.")
        return 0

    # 기존 관심사 조회 (중복 방지)
    existing_interests = {
        (ui.user_id, ui.category_id)
        for ui in db.query(UserInterest).all()
    }

    created_count = 0

    for user in users:
        # 이미 관심사가 있는 사용자는 스킵
        if any(user.id == ui[0] for ui in existing_interests):
            logger.info(f"User '{user.username}' already has interests, skipping...")
            continue

        # 랜덤 개수 결정
        num_interests = random.randint(min_interests, max_interests)
        
        # 랜덤 카테고리 선택
        selected_categories = random.sample(categories, min(num_interests, len(categories)))

        for category in selected_categories:
            user_interest = UserInterest(
                user_id=user.id,
                category_id=category.id,
            )
            db.add(user_interest)
            created_count += 1

        category_codes = [c.code for c in selected_categories]
        logger.info(
            f"Assigned {len(selected_categories)} interests to '{user.username}': {category_codes}"
        )

    db.commit()
    logger.info(f"✅ Total {created_count} user interests created.")
    return created_count


def seed_user_interests_standalone() -> None:
    """
    독립적으로 실행 가능한 함수 (CLI에서 호출용).
    """
    db = next(get_db())
    try:
        seed_user_interests(db)
    finally:
        db.close()


if __name__ == "__main__":
    seed_user_interests_standalone()
