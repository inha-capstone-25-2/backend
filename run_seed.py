"""
Dev 환경용 Mock 데이터 생성 CLI 스크립트.

PostgreSQL과 MongoDB 테이블에 mock 데이터를 삽입합니다.
- dev 환경에서만 실행됩니다.
- PostgreSQL: Categories → Users → UserInterests
- MongoDB: Bookmarks, UserActivities, SearchHistory (papers 제외)

사용 예시:
    python run_seed.py
    python run_seed.py --only=users
    python run_seed.py --only=bookmarks
    python run_seed.py --mongo-only  # MongoDB만
    python run_seed.py --postgres-only  # PostgreSQL만
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
from app.seed.bookmarks_seed import seed_bookmarks
from app.seed.activities_seed import seed_activities
from app.seed.search_history_seed import seed_search_history
from app.seed.papers_enrichment_seed import enrich_papers
from app.db.postgres import get_db
from app.db.mongodb import get_mongo_db, init_mongo

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


def seed_postgres_all() -> None:
    """
    모든 PostgreSQL 테이블에 mock 데이터를 시딩합니다.
    """
    logger.info("\n" + "=" * 60)
    logger.info("PostgreSQL Mock Data Seeding")
    logger.info("=" * 60)

    db = next(get_db())
    try:
        # 1. Categories
        logger.info("\n[1/3] Seeding Categories...")
        seed_categories(db)

        # 2. Users
        logger.info("\n[2/3] Seeding Users (500 users)...")
        seed_users(db)

        # 3. UserInterests
        logger.info("\n[3/3] Seeding User Interests...")
        seed_user_interests(db)

    except Exception as e:
        logger.error(f"❌ Error during PostgreSQL seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()

    logger.info("\n✅ PostgreSQL seeding completed!")


def seed_mongo_all() -> None:
    """
    모든 MongoDB 컬렉션에 mock 데이터를 시딩합니다 (papers 제외).
    """
    logger.info("\n" + "=" * 60)
    logger.info("MongoDB Mock Data Seeding")
    logger.info("=" * 60)

    # MongoDB 초기화
    init_mongo()
    
    db = next(get_mongo_db())
    
    try:
        # 1. Bookmarks
        logger.info("\n[1/4] Seeding Bookmarks (500 bookmarks)...")
        seed_bookmarks(db)

        # 2. User Activities
        logger.info("\n[2/4] Seeding User Activities (1,000 activities)...")
        seed_activities(db)

        # 3. Search History
        logger.info("\n[3/4] Seeding Search History (300 searches)...")
        seed_search_history(db)
        
        # 4. Papers Enrichment
        logger.info("\n[4/4] Enriching Papers collection...")
        enrich_papers(db)

    except Exception as e:
        logger.error(f"❌ Error during MongoDB seeding: {e}")
        raise

    logger.info("\n✅ MongoDB seeding completed!")


def seed_all() -> None:
    """
    PostgreSQL과 MongoDB 모두에 mock 데이터를 시딩합니다.
    """
    logger.info("=" * 60)
    logger.info("Starting FULL mock data seeding...")
    logger.info("=" * 60)

    seed_postgres_all()
    seed_mongo_all()

    logger.info("\n" + "=" * 60)
    logger.info("✅ All mock data seeding completed successfully!")
    logger.info("=" * 60)


def seed_categories_only() -> None:
    logger.info("Seeding Categories only...")
    db = next(get_db())
    try:
        seed_categories(db)
        logger.info("✅ Categories seeding completed!")
    finally:
        db.close()


def seed_users_only() -> None:
    logger.info("Seeding Users only...")
    db = next(get_db())
    try:
        seed_users(db)
        logger.info("✅ Users seeding completed!")
    finally:
        db.close()


def seed_interests_only() -> None:
    logger.info("Seeding User Interests only...")
    db = next(get_db())
    try:
        seed_user_interests(db)
        logger.info("✅ User Interests seeding completed!")
    finally:
        db.close()


def seed_bookmarks_only() -> None:
    logger.info("Seeding Bookmarks only...")
    db = next(get_mongo_db())
    seed_bookmarks(db)
    logger.info("✅ Bookmarks seeding completed!")


def seed_activities_only() -> None:
    logger.info("Seeding User Activities only...")
    db = next(get_mongo_db())
    seed_activities(db)
    logger.info("✅ User Activities seeding completed!")


def seed_searches_only() -> None:
    logger.info("Seeding Search History only...")
    db = next(get_mongo_db())
    seed_search_history(db)
    logger.info("✅ Search History seeding completed!")


def enrich_papers_only() -> None:
    logger.info("Enriching Papers collection only...")
    db = next(get_mongo_db())
    enrich_papers(db)
    logger.info("✅ Papers enrichment completed!")


def main():
    parser = argparse.ArgumentParser(
        description="Dev 환경용 Mock 데이터 생성 CLI"
    )
    parser.add_argument(
        "--only",
        choices=["categories", "users", "interests", "bookmarks", "activities", "searches", "papers", "all"],
        default="all",
        help="특정 테이블/컬렉션만 시딩 (기본값: all)",
    )
    parser.add_argument(
        "--postgres-only",
        action="store_true",
        help="PostgreSQL만 시딩",
    )
    parser.add_argument(
        "--mongo-only",
        action="store_true",
        help="MongoDB만 시딩",
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
    if args.postgres_only:
        seed_postgres_all()
    elif args.mongo_only:
        seed_mongo_all()
    elif args.only == "categories":
        seed_categories_only()
    elif args.only == "users":
        seed_users_only()
    elif args.only == "interests":
        seed_interests_only()
    elif args.only == "bookmarks":
        seed_bookmarks_only()
    elif args.only == "activities":
        seed_activities_only()
    elif args.only == "searches":
        seed_searches_only()
    elif args.only == "papers":
        enrich_papers_only()
    else:
        seed_all()


if __name__ == "__main__":
    main()
