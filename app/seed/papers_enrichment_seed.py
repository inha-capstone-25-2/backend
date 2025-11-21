"""
Dev 환경용 Papers 컬렉션 Enrichment 스크립트.

기존 papers 컬렉션의 문서들에 다음 필드를 추가합니다:
- bookmark_count: 북마크 수
- view_count: 조회 수
- embedding_vector: 임베딩 벡터 (300~500차원)
- summary: 요약 (한글/영문)
- difficulty_level: 난이도 레벨
- keywords: 키워드 배열

주의: papers 컬렉션이 존재할 때만 실행됩니다.
"""
from __future__ import annotations
import logging
import random
from typing import TYPE_CHECKING
from faker import Faker
import numpy as np
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError

if TYPE_CHECKING:
    from pymongo.database import Database

logger = logging.getLogger(__name__)

# Faker 인스턴스
fake_en = Faker("en_US")
fake_ko = Faker("ko_KR")

# 난이도 레벨
DIFFICULTY_LEVELS = ["beginner", "intermediate", "advanced"]

# 키워드 풀 (arXiv 관련)
KEYWORD_POOL = [
    "machine learning", "deep learning", "neural networks", "transformers",
    "computer vision", "natural language processing", "reinforcement learning",
    "generative models", "optimization", "graph neural networks",
    "attention mechanism", "convolutional networks", "recurrent networks",
    "transfer learning", "self-supervised learning", "adversarial training",
    "multi-modal learning", "few-shot learning", "meta-learning",
    "knowledge distillation", "model compression", "federated learning",
    "explainable AI", "fairness", "robustness", "uncertainty quantification"
]


def generate_embedding_vector(dim: int = None) -> list[float]:
    """
    랜덤 임베딩 벡터 생성 (300~500차원).
    
    Args:
        dim: 벡터 차원 (기본값: 300~500 사이 랜덤)
    
    Returns:
        정규화된 float 벡터
    """
    if dim is None:
        dim = random.randint(300, 500)
    
    # 평균 0, 표준편차 1인 정규분포에서 샘플링
    vector = np.random.randn(dim)
    
    # L2 정규화 (단위 벡터로 변환)
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm
    
    return vector.tolist()


def generate_summary() -> dict[str, str]:
    """
    한글/영문 요약 생성.
    
    Returns:
        {"ko": "한글 요약", "en": "English summary"}
    """
    return {
        "ko": fake_ko.text(max_nb_chars=200),
        "en": fake_en.text(max_nb_chars=200)
    }


def generate_keywords(count: int = None) -> list[str]:
    """
    랜덤 키워드 배열 생성.
    
    Args:
        count: 키워드 개수 (기본값: 3~7 사이 랜덤)
    
    Returns:
        키워드 배열
    """
    if count is None:
        count = random.randint(3, 7)
    
    return random.sample(KEYWORD_POOL, min(count, len(KEYWORD_POOL)))


def enrich_papers(db: Database, batch_size: int = 100) -> int:
    """
    papers 컬렉션에 enrichment 필드 추가.
    
    Args:
        db: MongoDB Database 객체
        batch_size: 배치 크기 (기본값: 100)
    
    Returns:
        업데이트된 문서 수
    """
    from app.core.settings import settings
    
    collection = db[settings.mongo_collection]
    
    # 컬렉션 존재 확인
    if settings.mongo_collection not in db.list_collection_names():
        logger.warning(f"Collection '{settings.mongo_collection}' does not exist. Skipping enrichment.")
        return 0
    
    total_count = collection.count_documents({})
    if total_count == 0:
        logger.warning("Papers collection is empty. No documents to enrich.")
        return 0
    
    logger.info(f"Found {total_count} papers to enrich.")
    
    # 배치 업데이트 준비
    operations = []
    cursor = collection.find({}, {"_id": 1})
    
    enriched_count = 0
    
    for doc in cursor:
        paper_id = doc["_id"]
        
        # Enrichment 데이터 생성
        enrichment_data = {
            "bookmark_count": random.randint(0, 500),
            "view_count": random.randint(0, 10000),
            "embedding_vector": generate_embedding_vector(),
            "summary": generate_summary(),
            "difficulty_level": random.choice(DIFFICULTY_LEVELS),
            "keywords": generate_keywords()
        }
        
        operations.append(
            UpdateOne(
                {"_id": paper_id},
                {"$set": enrichment_data}
            )
        )
        
        # 배치 실행
        if len(operations) >= batch_size:
            try:
                result = collection.bulk_write(operations, ordered=False)
                enriched_count += result.modified_count
                logger.info(f"Enriched {enriched_count}/{total_count} papers...")
            except BulkWriteError as e:
                logger.warning(f"Bulk write error: {e.details}")
                enriched_count += e.details.get("nModified", 0)
            
            operations.clear()
    
    # 남은 배치 처리
    if operations:
        try:
            result = collection.bulk_write(operations, ordered=False)
            enriched_count += result.modified_count
        except BulkWriteError as e:
            logger.warning(f"Bulk write error: {e.details}")
            enriched_count += e.details.get("nModified", 0)
    
    logger.info(f"Enrichment complete: {enriched_count}/{total_count} papers updated.")
    return enriched_count


def enrich_papers_standalone() -> None:
    """
    독립 실행용 래퍼 함수.
    """
    from app.db.mongodb import init_mongo, get_mongo_client_direct
    from app.core.settings import settings
    
    init_mongo()
    client = get_mongo_client_direct()
    db = client[settings.mongo_db]
    
    enrich_papers(db)


if __name__ == "__main__":
    enrich_papers_standalone()
