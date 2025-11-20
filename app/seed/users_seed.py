"""
Dev 환경용 Mock 사용자 데이터 생성 스크립트.

20명의 테스트 사용자를 생성합니다.
비밀번호는 모두 'test1234'로 통일됩니다.
"""
from __future__ import annotations
import logging
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.models.user import User
from app.db.postgres import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MOCK_USERS = [
    {"username": "alice_kim", "email": "alice.kim@example.com", "name": "김앨리스"},
    {"username": "bob_lee", "email": "bob.lee@example.com", "name": "이밥"},
    {"username": "charlie_park", "email": "charlie.park@example.com", "name": "박찰리"},
    {"username": "david_choi", "email": "david.choi@example.com", "name": "최데이비드"},
    {"username": "emma_jung", "email": "emma.jung@example.com", "name": "정엠마"},
    {"username": "frank_kang", "email": "frank.kang@example.com", "name": "강프랭크"},
    {"username": "grace_han", "email": "grace.han@example.com", "name": "한그레이스"},
    {"username": "henry_shin", "email": "henry.shin@example.com", "name": "신헨리"},
    {"username": "irene_kwon", "email": "irene.kwon@example.com", "name": "권아이린"},
    {"username": "jack_yoon", "email": "jack.yoon@example.com", "name": "윤잭"},
    {"username": "kate_lim", "email": "kate.lim@example.com", "name": "임케이트"},
    {"username": "leo_song", "email": "leo.song@example.com", "name": "송리오"},
    {"username": "mia_jang", "email": "mia.jang@example.com", "name": "장미아"},
    {"username": "noah_bae", "email": "noah.bae@example.com", "name": "배노아"},
    {"username": "olivia_oh", "email": "olivia.oh@example.com", "name": "오올리비아"},
    {"username": "peter_nam", "email": "peter.nam@example.com", "name": "남피터"},
    {"username": "quinn_seo", "email": "quinn.seo@example.com", "name": "서퀸"},
    {"username": "ryan_hong", "email": "ryan.hong@example.com", "name": "홍라이언"},
    {"username": "sophia_go", "email": "sophia.go@example.com", "name": "고소피아"},
    {"username": "thomas_ahn", "email": "thomas.ahn@example.com", "name": "안토마스"},
]

DEFAULT_PASSWORD = "test1234"


def seed_users(db: Session) -> list[User]:
    """
    MOCK_USERS 기준으로 사용자를 생성합니다.
    - 이미 존재하는 username/email은 스킵
    - 비밀번호는 모두 'test1234'로 해시화
    """
    hashed_password = pwd_context.hash(DEFAULT_PASSWORD)
    created_users = []

    existing_usernames = {u.username for u in db.query(User.username).all()}
    existing_emails = {u.email for u in db.query(User.email).all()}

    for user_data in MOCK_USERS:
        username = user_data["username"]
        email = user_data["email"]

        if username in existing_usernames:
            logger.info(f"User '{username}' already exists, skipping...")
            continue

        if email in existing_emails:
            logger.info(f"Email '{email}' already exists, skipping...")
            continue

        user = User(
            username=username,
            email=email,
            name=user_data["name"],
            hashed_password=hashed_password,
            is_active=True,
            token_version=0,
        )
        db.add(user)
        created_users.append(user)
        logger.info(f"Created user: {username} ({email})")

    db.commit()
    logger.info(f"✅ Total {len(created_users)} users created.")
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
