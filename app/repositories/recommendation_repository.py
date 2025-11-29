import logging
from datetime import datetime
from typing import List, Dict, Any

from pymongo.database import Database
from pymongo.collection import Collection

from app.core.constants import COLLECTION_PAPER_RECOMMENDATIONS

logger = logging.getLogger(__name__)


class RecommendationRepository:
    def __init__(self, db: Database):
        self.db = db
        self.recommendations_collection: Collection = db[
            COLLECTION_PAPER_RECOMMENDATIONS
        ]

    def log_recommendation(
        self,
        user_id: int,
        paper_id: str,
        recommendation_type: str,
        score: float,
        breakdown: Dict[str, float],
        reasons: List[str],
    ) -> None:
        """추천 결과를 MongoDB에 로깅"""
        log_doc = {
            "user_id": user_id,
            "paper_id": paper_id,
            "recommendation_type": recommendation_type,
            "score": score,
            "features": {
                "interest_score": breakdown.get("interest_score", 0.0),
                "popularity_score": breakdown.get("popularity_score", 0.0),
                "recency_score": breakdown.get("recency_score", 0.0),
                "personalization_score": breakdown.get("personalization_score", 0.0),
            },
            "context": {"reasons": reasons},
            "was_clicked": False,
            "recommended_at": datetime.utcnow(),
        }

        try:
            self.recommendations_collection.insert_one(log_doc)
        except Exception as e:
            logger.error(f"Failed to log recommendation: {e}")

    def log_recommendations_batch(self, log_docs: List[Dict[str, Any]]) -> None:
        """추천 결과를 배치로 MongoDB에 로깅"""
        if not log_docs:
            return

        try:
            self.recommendations_collection.insert_many(log_docs, ordered=False)
            logger.info(f"Logged {len(log_docs)} recommendations in batch")
        except Exception as e:
            logger.error(f"Failed to log recommendations batch: {e}")

    def get_all_recommendations(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[int, List[Dict[str, Any]]]:
        """전체 추천 로그 조회 (페이지네이션)"""
        try:
            # 전체 개수 조회
            total = self.recommendations_collection.count_documents({})

            # 페이지네이션 조회 (최신순 정렬)
            skip = (page - 1) * page_size
            cursor = (
                self.recommendations_collection.find({})
                .sort("recommended_at", -1)
                .skip(skip)
                .limit(page_size)
            )

            items = list(cursor)
            return total, items

        except Exception as e:
            logger.error(f"Failed to get all recommendations: {e}")
            return 0, []

    def get_recommendations_by_user(
        self, user_id: int, page: int = 1, page_size: int = 20
    ) -> tuple[int, List[Dict[str, Any]]]:
        """특정 사용자의 추천 로그 조회 (페이지네이션)"""
        try:
            # 사용자별 개수 조회
            query = {"user_id": user_id}
            total = self.recommendations_collection.count_documents(query)

            # 페이지네이션 조회 (최신순 정렬)
            skip = (page - 1) * page_size
            cursor = (
                self.recommendations_collection.find(query)
                .sort("recommended_at", -1)
                .skip(skip)
                .limit(page_size)
            )

            items = list(cursor)
            return total, items

        except Exception as e:
            logger.error(f"Failed to get recommendations by user {user_id}: {e}")
            return 0, []

