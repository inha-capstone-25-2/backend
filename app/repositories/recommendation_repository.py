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

