import logging
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from pymongo.database import Database

from app.repositories.recommendation_repository import RecommendationRepository
from app.utils.rule_based_recommender import RuleBasedRecommender
from app.utils.mongodb import serialize_object_id
from app.models.user import User
from app.schemas.recommendation import RecommendationItem, ScoreBreakdown

logger = logging.getLogger(__name__)


class RecommendationService:
    def __init__(self, db_mongo: Database):
        self.db_mongo = db_mongo
        self.repo = RecommendationRepository(db_mongo)

    def get_recommendations(
        self, user: User, db_postgres: Session, top_k: int, candidate_limit: int = 100
    ) -> Dict[str, Any]:
        """사용자 맞춤 논문 추천 및 로깅"""

        logger.info(f"Generating recommendations for user {user.id}")

        # 1. 추천 생성
        recommender = RuleBasedRecommender()
        recommendations = recommender.recommend(
            user=user,
            db_postgres=db_postgres,
            db_mongo=self.db_mongo,
            top_k=top_k,
            candidate_limit=candidate_limit,
        )

        # 2. 추천 로깅
        for rec in recommendations:
            self.repo.log_recommendation(
                user_id=user.id,
                paper_id=rec.get("paper_id"),
                recommendation_type="rule_based",
                score=rec.get("total_score", 0.0),
                breakdown=rec.get("breakdown", {}),
                reasons=rec.get("reasons", []),
            )

        # 3. 응답 생성
        recommendation_items = []
        for rec in recommendations:
            paper = rec["paper"]
            serialize_object_id(paper)
            paper["id"] = paper.pop("_id")

            item = RecommendationItem(
                paper_id=rec["paper_id"],
                title=paper.get("title", ""),
                abstract=paper.get("abstract"),
                authors=paper.get("authors"),
                categories=paper.get("categories", []),
                keywords=paper.get("keywords", []),
                difficulty_level=paper.get("difficulty_level"),
                view_count=paper.get("view_count", 0),
                bookmark_count=paper.get("bookmark_count", 0),
                update_date=paper.get("update_date"),
                total_score=rec["total_score"],
                breakdown=ScoreBreakdown(**rec["breakdown"]),
                reasons=rec["reasons"],
            )
            recommendation_items.append(item)

        return {
            "user_id": user.id,
            "recommendation_type": "rule_based",
            "recommendations": recommendation_items,
            "total_count": len(recommendation_items),
            "timestamp": datetime.utcnow().isoformat(),
        }
