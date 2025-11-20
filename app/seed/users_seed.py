"""
Dev 환경용 Mock 사용자 데이터 생성 스크립트.

500명의 테스트 사용자를 생성합니다.
비밀번호는 모두 'test1234'로 통일됩니다.
"""
from __future__ import annotations
import logging
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from faker import Faker

from app.models.user import User
from app.db.postgres import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
fake = Faker(['ko_KR'])  # 한국어 로케일

DEFAULT_PASSWORD = "test1234"
NUM_USERS = 500


def seed_users(db: Session) -> list[User]:
    """
    Faker를 사용하여 500명의 사용자를 생성합니다.
    - 이미 존재하는 username/email은 스킵
    - 비밀번호는 모두 'test1234'로 해시화
    """
    hashed_password = pwd_context.hash(DEFAULT_PASSWORD)
    created_users = []

    existing_usernames = {u.username for u in db.query(User.username).all()}
    existing_emails = {u.email for u in db.query(User.email).all()}

    logger.info(f"Generating {NUM_USERS} mock users...")

    for i in range(NUM_USERS):
        # Username: user_0001, user_0002, ...
        username = f"user_{i+1:04d}"
        
        # Email: user_0001@example.com
        email = f"{username}@example.com"
        
        # 이미 존재하는지 체크
        if username in existing_usernames or email in existing_emails:
            logger.debug(f"User '{username}' already exists, skipping...")
            continue

        # 한글 이름 생성
        name = fake.name()

        user = User(
            username=username,
            email=email,
            name=name,
            hashed_password=hashed_password,
            is_active=True,
            token_version=0,
        )
        created_users.append(user)

        # 100명마다 로그 출력
        if (i + 1) % 100 == 0:
            logger.info(f"Generated {i + 1}/{NUM_USERS} users...")

    # Bulk insert for performance
    if created_users:
        db.bulk_save_objects(created_users)
        db.commit()
        logger.info(f"✅ Total {len(created_users)} users created successfully!")
    else:
        logger.info("No new users to create.")

    return created_users


def seed_users_standalone() -> None:
    """
    독립적으로 실행 가능한 함수 (CLI에서 호출용).
    """
    db = next(get_db())
    try:
        seed_users(db)
    finally:
        db.close()


if __name__ == "__main__":
    seed_users_standalone()
