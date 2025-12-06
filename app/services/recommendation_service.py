"""추천 서비스 모듈.

사용자 맞춤 논문 추천의 비즈니스 로직을 담당합니다.
"""

import logging
import time
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from pymongo.database import Database

from app.repositories.recommendation_repository import RecommendationRepository
from app.utils.rule_based_recommender import RuleBasedRecommender
from app.utils.mongodb import serialize_object_id
from app.models.user import User
from app.schemas.recommendation import RecommendationItem, ScoreBreakdown
from app.schemas.paper import Summary
from app.schemas.recommendation_event import ActivityType

logger = logging.getLogger(__name__)


class RecommendationService:
    """추천 서비스.

    Attributes:
        db_mongo: MongoDB 데이터베이스 인스턴스.
        repo: 추천 저장소 인스턴스.
    """

    def __init__(self, db_mongo: Database):
        """인스턴스를 초기화한다.

        Args:
            db_mongo: MongoDB 데이터베이스 인스턴스.
        """
        self.db_mongo = db_mongo
        self.repo = RecommendationRepository(db_mongo)

    def get_recommendations(
        self, user: User, db_postgres: Session, top_k: int, candidate_limit: int = 50  # 100 -> 50으로 축소
    ) -> Dict[str, Any]:
        """사용자 맞춤 논문 추천 및 로깅"""
        
        start_time = time.time()
        logger.info(f"Generating recommendations for user {user.id}")

        import uuid
        session_id = str(uuid.uuid4())
        logger.info(f"Generated session_id: {session_id}")

        step_start = time.time()
        recommender = RuleBasedRecommender()
        all_recommendations = recommender.recommend(
            user=user,
            db_postgres=db_postgres,
            db_mongo=self.db_mongo,
            top_k=None,
            candidate_limit=candidate_limit,
        )
        logger.info(f"[PERF] Recommender.recommend took {time.time() - step_start:.3f}s")

        all_candidate_ids = [rec.get("paper_id") for rec in all_recommendations]
        
        candidates_features_dict = {
            rec.get("paper_id"): rec.get("breakdown", {}) 
            for rec in all_recommendations
        }
        
        candidates_scores_dict = {
            rec.get("paper_id"): rec.get("total_score", 0.0)
            for rec in all_recommendations
        }

        recommendations = all_recommendations[:top_k]
        
        final_display = [rec.get("paper_id") for rec in recommendations]

        step_start = time.time()
        log_docs = []
        for rec in recommendations:
            log_doc = {
                "session_id": session_id,
                "user_id": user.id,
                "paper_id": rec.get("paper_id"),
                "recommendation_type": "rule_based",
                "score": rec.get("total_score", 0.0),
                "features": {
                    "interest_score": rec.get("breakdown", {}).get("interest_score", 0.0),
                    "popularity_score": rec.get("breakdown", {}).get("popularity_score", 0.0),
                    "recency_score": rec.get("breakdown", {}).get("recency_score", 0.0),
                    "personalization_score": rec.get("breakdown", {}).get("personalization_score", 0.0),
                },
                "context": {"reasons": rec.get("reasons", [])},
                "was_clicked": False,
                "recommended_at": datetime.utcnow(),
            }
            log_docs.append(log_doc)
        
        self.repo.log_recommendations_batch(log_docs)
        logger.info(f"[PERF] Batch logging took {time.time() - step_start:.3f}s")

        step_start = time.time()
        self.repo.log_session_context(
            user_id=user.id,
            session_id=session_id,
            context_data={
                "candidates": all_candidate_ids,
                "candidates_features": candidates_features_dict,
                "candidates_scores": candidates_scores_dict,
                "final_display": final_display,
            }
        )
        logger.info(f"[PERF] Session context logging took {time.time() - step_start:.3f}s")

        step_start = time.time()
        for idx, rec in enumerate(recommendations):
            self.repo.log_event(
                user_id=user.id,
                paper_id=rec.get("paper_id"),
                activity_type=ActivityType.EXPOSE.value,
                session_id=session_id,
                metadata={"position": idx}
            )
        logger.info(f"[PERF] Expose event logging took {time.time() - step_start:.3f}s")

        step_start = time.time()
        recommendation_items = []
        for rec in recommendations:
            paper = rec["paper"]
            serialize_object_id(paper)
            paper["id"] = paper.pop("_id")

            summary_data = paper.get("summary")
            summary_obj = Summary(**summary_data) if summary_data else None

            item = RecommendationItem(
                paper_id=rec["paper_id"],
                title=paper.get("title", ""),
                summary=summary_obj,
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
        
        logger.info(f"[PERF] Response generation took {time.time() - step_start:.3f}s")
        logger.info(f"[PERF] Total service time: {time.time() - start_time:.3f}s")

        return {
            "user_id": user.id,
            "session_id": session_id,
            "recommendation_type": "rule_based",
            "recommendations": recommendation_items,
            "total_count": len(recommendation_items),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def get_all_recommendation_logs(
        self, page: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        """전체 추천 로그 조회"""
        logger.info(f"Getting all recommendation logs (page={page}, page_size={page_size})")

        # Repository에서 데이터 조회
        total, items = self.repo.get_all_recommendations(page, page_size)

        # MongoDB _id를 문자열로 변환 및 recommended_at 포맷팅
        formatted_items = []
        for item in items:
            serialize_object_id(item)
            item["id"] = item.pop("_id")
            
            # recommended_at을 ISO 형식 문자열로 변환
            if "recommended_at" in item and hasattr(item["recommended_at"], "isoformat"):
                item["recommended_at"] = item["recommended_at"].isoformat()
            
            formatted_items.append(item)

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": formatted_items,
        }

    def get_user_recommendation_logs(
        self, user_id: int, page: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        """특정 사용자의 추천 로그 조회"""
        logger.info(
            f"Getting recommendation logs for user {user_id} (page={page}, page_size={page_size})"
        )

        # Repository에서 데이터 조회
        total, items = self.repo.get_recommendations_by_user(user_id, page, page_size)

        # MongoDB _id를 문자열로 변환 및 recommended_at 포맷팅
        formatted_items = []
        for item in items:
            serialize_object_id(item)
            item["id"] = item.pop("_id")
            
            # recommended_at을 ISO 형식 문자열로 변환
            if "recommended_at" in item and hasattr(item["recommended_at"], "isoformat"):
                item["recommended_at"] = item["recommended_at"].isoformat()
            
            formatted_items.append(item)

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": formatted_items,
        }

    def record_click(self, recommendation_id: str, user_id: int) -> Dict[str, Any]:
        """클릭 기록"""
        success = self.repo.mark_as_clicked(recommendation_id)
        if success:
            logger.info(f"Marked recommendation {recommendation_id} as clicked by user {user_id}")
        return {
            "success": success,
            "clicked_at": datetime.utcnow().isoformat() if success else None,
        }

    def record_interaction(
        self, recommendation_id: str, user_id: int, paper_id: str, interaction_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """상호작용 데이터 기록"""
        saved_doc = self.repo.save_interaction(
            recommendation_id, user_id, paper_id, interaction_data
        )
        
        if saved_doc:
            serialize_object_id(saved_doc)
            saved_doc["id"] = saved_doc.pop("_id")
            
            # datetime을 ISO 문자열로 변환
            for field in ["created_at", "updated_at"]:
                if field in saved_doc and hasattr(saved_doc[field], "isoformat"):
                    saved_doc[field] = saved_doc[field].isoformat()
            
            logger.info(f"Saved interaction for recommendation {recommendation_id}")
        
        return saved_doc

