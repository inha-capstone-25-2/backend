"""
Dev 환경용 Mock search_history 데이터 생성 스크립트.

300개의 검색 히스토리를 생성합니다.
"""
from __future__ import annotations
import logging
import random
from datetime import datetime, timedelta
from pymongo.database import Database
from faker import Faker

from app.db.mongodb import get_mongo_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

fake = Faker()
NUM_SEARCHES = 300

# ML/AI 관련 검색어 예시
SEARCH_QUERIES = [
    "transformer",
    "neural network",
    "deep learning",
    "GAN",
    "reinforcement learning",
    "computer vision",
    "natural language processing",
    "convolutional neural network",
    "recurrent neural network",
    "BERT",
    "GPT",
    "attention mechanism",
    "machine learning",
    "supervised learning",
    "unsupervised learning",
    "transfer learning",
    "image classification",
    "object detection",
    "semantic segmentation",
    "generative model",
]


def seed_search_history(db: Database) -> int:
    """
    300개의 mock search_history를 생성합니다.
    
    - 랜덤 검색어 (ML/AI 관련 키워드)
    - 랜덤 searched_at (최근 1개월 이내)
    - 랜덤 user_id (80% 확률로 설정, 20%는 익명)
    
    Returns:
        생성된 search_history 개수
    """
    search_history_coll = db["search_history"]
    
    # 기존 search_history 개수 확인
    existing_count = search_history_coll.count_documents({})
    logger.info(f"Existing search history: {existing_count}")
    
    searches = []
    now = datetime.utcnow()
    
    for i in range(NUM_SEARCHES):
        # 랜덤 검색어
        query = random.choice(SEARCH_QUERIES)
        
        # 랜덤 searched_at (최근 1개월)
        days_ago = random.randint(0, 30)
        searched_at = now - timedelta(days=days_ago, hours=random.randint(0, 23))
        
        # user_id (80% 확률로 설정)
        user_id = random.randint(1, 500) if random.random() > 0.2 else None
        
        search = {
            "query": query,
            "searched_at": searched_at,
        }
        
        if user_id:
            search["user_id"] = user_id
        
        # filters (선택적, 10% 확률)
        if random.random() > 0.9:
            search["filters"] = {
                "category": random.choice(["cs.AI", "cs.LG", "cs.CV", "cs.CL"])
            }
        
        searches.append(search)
        
        if (i + 1) % 100 == 0:
            logger.info(f"Generated {i + 1}/{NUM_SEARCHES} search histories...")
    
    # Bulk insert
    if searches:
        result = search_history_coll.insert_many(searches, ordered=False)
        logger.info(f"✅ Total {len(result.inserted_ids)} search histories created!")
        return len(result.inserted_ids)
    
    return 0


def seed_search_history_standalone() -> None:
    """
    독립적으로 실행 가능한 함수 (CLI에서 호출용).
    """
    db = next(get_mongo_db())
    seed_search_history(db)


if __name__ == "__main__":
    seed_search_history_standalone()
