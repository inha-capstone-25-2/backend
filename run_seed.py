"""
Dev 환경용 Mock 데이터 생성 CLI 스크립트.

PostgreSQL 테이블에 mock 데이터를 삽입합니다.
- dev 환경에서만 실행됩니다.
- Categories → Users → UserInterests 순서로 시딩합니다.

사용 예시:
    python run_seed.py
    python run_seed.py --only=users
    python run_seed.py --only=categories
    python run_seed.py --force  # dev 환경 체크 무시
"""
from __future__ import annotations
import argparse
import logging
import os
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
BACKEND_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.settings import settings
from app.seed.categories_seed import seed_categories
from app.seed.users_seed import seed_users
from app.seed.user_interests_seed import seed_user_interests
from app.db.postgres import get_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def check_environment(force: bool = False) -> None:
    """
    dev 환경인지 확인합니다.
    """
    app_env = settings.app_env.lower()
    
    if app_env != "dev" and not force:
        logger.error(
            f"❌ Current environment is '{app_env}'. "
            "Mock data seeding is only allowed in 'dev' environment."
        )
        logger.info("If you want to run anyway, use --force flag.")
        sys.exit(1)
    
    if force and app_env != "dev":
        logger.warning(f"⚠️ Force mode enabled. Seeding in '{app_env}' environment...")
    else:
        logger.info(f"✅ Environment check passed: {app_env}")


def seed_all() -> None:
    """
    모든 테이블에 mock 데이터를 시딩합니다.
    """
    logger.info("=" * 60)
    logger.info("Starting mock data seeding...")
    logger.info("=" * 60)

    db = next(get_db())
    try:
        # 1. Categories
        logger.info("\n[1/3] Seeding Categories...")
        seed_categories(db)

        # 2. Users
        logger.info("\n[2/3] Seeding Users...")
        seed_users(db)

        # 3. UserInterests
        logger.info("\n[3/3] Seeding User Interests...")
        seed_user_interests(db)

    except Exception as e:
        logger.error(f"❌ Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()

    logger.info("\n" + "=" * 60)
    logger.info("✅ Mock data seeding completed successfully!")
    logger.info("=" * 60)


def seed_categories_only() -> None:
    """
    Categories만 시딩합니다.
    """
    logger.info("Seeding Categories only...")
    db = next(get_db())
    try:
        seed_categories(db)
        logger.info("✅ Categories seeding completed!")
    finally:
        db.close()


def seed_users_only() -> None:
    """
    Users만 시딩합니다.
    """
    logger.info("Seeding Users only...")
    db = next(get_db())
    try:
        seed_users(db)
        logger.info("✅ Users seeding completed!")
    finally:
        db.close()


def seed_interests_only() -> None:
    """
    UserInterests만 시딩합니다.
    """
    logger.info("Seeding User Interests only...")
    db = next(get_db())
    try:
        seed_user_interests(db)
        logger.info("✅ User Interests seeding completed!")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Dev 환경용 Mock 데이터 생성 CLI"
    )
    parser.add_argument(
        "--only",
        choices=["categories", "users", "interests", "all"],
        default="all",
        help="특정 테이블만 시딩 (기본값: all)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="dev 환경 체크 무시 (위험: 주의해서 사용)",
    )

    args = parser.parse_args()

    # 환경 체크
    check_environment(force=args.force)

    # 시딩 실행
    if args.only == "categories":
        seed_categories_only()
    elif args.only == "users":
        seed_users_only()
    elif args.only == "interests":
        seed_interests_only()
    else:
        seed_all()


if __name__ == "__main__":
    main()
