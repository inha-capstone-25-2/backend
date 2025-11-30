import logging
from datetime import datetime
from typing import List, Dict, Any

from pymongo.database import Database
from pymongo.collection import Collection
from bson import ObjectId

from app.core.constants import (
    COLLECTION_PAPER_RECOMMENDATIONS,
    COLLECTION_RECOMMENDATION_INTERACTIONS,
    COLLECTION_RECOMMENDATION_EVENTS,
)

logger = logging.getLogger(__name__)


class RecommendationRepository:
    def __init__(self, db: Database):
        self.db = db
        self.recommendations_collection: Collection = db[
            COLLECTION_PAPER_RECOMMENDATIONS
        ]
        self.interactions_collection: Collection = db[
            COLLECTION_RECOMMENDATION_INTERACTIONS
        ]
        self.events_collection: Collection = db[
            COLLECTION_RECOMMENDATION_EVENTS
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

    def mark_as_clicked(self, recommendation_id: str) -> bool:
        """추천 논문 클릭 표시"""
        try:
            result = self.recommendations_collection.update_one(
                {"_id": ObjectId(recommendation_id)},
                {
                    "$set": {
                        "was_clicked": True,
                        "clicked_at": datetime.utcnow(),
                    }
                },
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to mark recommendation as clicked: {e}")
            return False

    def save_interaction(
        self, recommendation_id: str, user_id: int, paper_id: str, interaction_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """상호작용 데이터 저장 (upsert)"""
        try:
            doc = {
                "recommendation_id": recommendation_id,
                "user_id": user_id,
                "paper_id": paper_id,
                **interaction_data,
                "updated_at": datetime.utcnow(),
            }

            # created_at은 최초 생성시에만
            result = self.interactions_collection.update_one(
                {"recommendation_id": recommendation_id},
                {
                    "$set": doc,
                    "$setOnInsert": {"created_at": datetime.utcnow()},
                },
                upsert=True,
            )

            # 저장된 문서 조회
            saved_doc = self.interactions_collection.find_one(
                {"recommendation_id": recommendation_id}
            )
            return saved_doc

        except Exception as e:
            logger.error(f"Failed to save interaction: {e}")
            return None

    def get_user_interactions(
        self, user_id: int, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """사용자별 상호작용 이력 조회"""
        try:
            cursor = (
                self.interactions_collection.find({"user_id": user_id})
                .sort("created_at", -1)
                .limit(limit)
            )
            return list(cursor)
        except Exception as e:
            logger.error(f"Failed to get user interactions: {e}")
            return []

    def log_event(
        self,
        user_id: int,
        paper_id: str,
        activity_type: str,
        session_id: str,
        metadata: Dict[str, Any] = None,
    ) -> str:
        """추천 이벤트 로깅"""
        event_doc = {
            "user_id": user_id,
            "paper_id": paper_id,
            "activity_type": activity_type,
            "timestamp": datetime.utcnow(),
            "session_id": session_id,
            "metadata": metadata or {},
        }

        try:
            result = self.events_collection.insert_one(event_doc)
            logger.info(
                f"Logged event: {activity_type} for paper {paper_id} "
                f"by user {user_id} in session {session_id}"
            )
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to log event: {e}")
            return None

    def get_events_by_session(
        self, session_id: str, page: int = 1, page_size: int = 50
    ) -> tuple[int, List[Dict[str, Any]]]:
        """세션별 이벤트 조회 (시간순 정렬)"""
        try:
            query = {"session_id": session_id}
            total = self.events_collection.count_documents(query)

            skip = (page - 1) * page_size
            cursor = (
                self.events_collection.find(query)
                .sort("timestamp", 1)  # 시간순 오름차순
                .skip(skip)
                .limit(page_size)
            )

            items = list(cursor)
            return total, items

        except Exception as e:
            logger.error(f"Failed to get events for session {session_id}: {e}")
            return 0, []

    def get_events_by_user(
        self, user_id: int, page: int = 1, page_size: int = 50
    ) -> tuple[int, List[Dict[str, Any]]]:
        """사용자별 이벤트 조회 (최신순 정렬)"""
        try:
            query = {"user_id": user_id}
            total = self.events_collection.count_documents(query)

            skip = (page - 1) * page_size
            cursor = (
                self.events_collection.find(query)
                .sort("timestamp", -1)  # 최신순 내림차순
                .skip(skip)
                .limit(page_size)
            )

            items = list(cursor)
            return total, items

        except Exception as e:
            logger.error(f"Failed to get events for user {user_id}: {e}")
            return 0, []


