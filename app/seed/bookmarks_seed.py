"""
Dev 환경용 Mock bookmarks 데이터 생성 스크립트.

500개의 북마크 데이터를 생성합니다.
"""
from __future__ import annotations
import logging
import random
from datetime import datetime, timedelta
from pymongo.database import Database
from faker import Faker

from app.db.mongodb import get_mongo_db
from app.core.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

fake = Faker()
NUM_BOOKMARKS = 500


def seed_bookmarks(db: Database) -> int:
    """
    500개의 mock bookmarks를 생성합니다.
    
    - 랜덤 사용자 ID (1~500)
    - 랜덤 paper_id (실제 papers 컬렉션에서 샘플링)
    - 랜덤 bookmarked_at (최근 6개월 이내)
    - 랜덤 notes (50% 확률로 null)
    
    Returns:
        생성된 bookmarks 개수
    """
    # papers 컬렉션에서 실제 논문 ID들 샘플링
    papers_coll = db[settings.mongo_collection]
    paper_ids = list(papers_coll.find({}, {"_id": 1}).limit(1000))
    
    if not paper_ids:
        logger.error("❌ No papers found in collection. Please load papers first.")
        logger.info("Run: python -c \"from app.loader.arxiv_mongo import copy_prod_to_local_mongo; copy_prod_to_local_mongo()\"")
        return 0
    
    logger.info(f"Found {len(paper_ids)} papers for bookmark references")
    
    bookmarks_coll = db["bookmarks"]
    
    # 기존 bookmarks 개수 확인
    existing_count = bookmarks_coll.count_documents({})
    logger.info(f"Existing bookmarks: {existing_count}")
    
    bookmarks = []
    now = datetime.utcnow()
    
    for i in range(NUM_BOOKMARKS):
        # 랜덤 사용자 ID (1~500)
        user_id = random.randint(1, 500)
        
        # 랜덤 paper_id
        paper = random.choice(paper_ids)
        paper_id = paper["_id"]
        
        # 랜덤 bookmarked_at (최근 6개월)
        days_ago = random.randint(0, 180)
        bookmarked_at = now - timedelta(days=days_ago, hours=random.randint(0, 23))
        
        # notes (50% 확률로 null, 나머지는 문장)
        notes = fake.sentence() if random.random() > 0.5 else None
        
        bookmark = {
            "user_id": user_id,
            "paper_id": paper_id,
            "bookmarked_at": bookmarked_at,
            "notes": notes,
        }
        bookmarks.append(bookmark)
        
        if (i + 1) % 100 == 0:
            logger.info(f"Generated {i + 1}/{NUM_BOOKMARKS} bookmarks...")
    
    # Bulk insert
    if bookmarks:
        result = bookmarks_coll.insert_many(bookmarks, ordered=False)
        logger.info(f"✅ Total {len(result.inserted_ids)} bookmarks created!")
        return len(result.inserted_ids)
    
    return 0


def seed_bookmarks_standalone() -> None:
    """
    독립적으로 실행 가능한 함수 (CLI에서 호출용).
    """
    db = next(get_mongo_db())
    seed_bookmarks(db)


if __name__ == "__main__":
    seed_bookmarks_standalone()
