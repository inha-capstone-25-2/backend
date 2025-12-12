"""추천 저장소 모듈.

추천 로그, 상호작용 데이터, 추천 이벤트의 CRUD 연산을 담당합니다.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.errors import PyMongoError
from bson import ObjectId

from app.core.constants import (
    COLLECTION_PAPER_RECOMMENDATIONS,
    COLLECTION_RECOMMENDATION_INTERACTIONS,
    COLLECTION_RECOMMENDATION_EVENTS,
)

logger = logging.getLogger(__name__)


class RecommendationRepository:
    """추천 데이터 저장소.

    Attributes:
        db: MongoDB 데이터베이스 인스턴스.
        recommendations_collection: 추천 로그 컬렉션.
        interactions_collection: 상호작용 컬렉션.
        events_collection: 추천 이벤트 컬렉션.
    """

    def __init__(self, db: Database):
        """인스턴스를 초기화한다.

        Args:
            db: MongoDB 데이터베이스 인스턴스.
        """
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
        session_id: str = None,
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
        
        if session_id:
            log_doc["session_id"] = session_id

        try:
            self.recommendations_collection.insert_one(log_doc)
        except PyMongoError as e:
            logger.error(f"Failed to log recommendation: {e}")

    def log_recommendations_batch(self, log_docs: List[Dict[str, Any]]) -> None:
        """추천 결과를 배치로 MongoDB에 로깅"""
        if not log_docs:
            return

        try:
            self.recommendations_collection.insert_many(log_docs, ordered=False)
            logger.info(f"Logged {len(log_docs)} recommendations in batch")
        except PyMongoError as e:
            logger.error(f"Failed to log recommendations batch: {e}")

    def get_all_recommendations(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[int, List[Dict[str, Any]]]:
        """전체 추천 로그 조회 (페이지네이션)"""
        try:
            total = self.recommendations_collection.count_documents({})

            skip = (page - 1) * page_size
            cursor = (
                self.recommendations_collection.find({})
                .sort("recommended_at", -1)
                .skip(skip)
                .limit(page_size)
            )

            items = list(cursor)
            return total, items

        except PyMongoError as e:
            logger.error(f"Failed to get all recommendations: {e}")
            return 0, []

    def get_recommendations_by_user(
        self, user_id: int, page: int = 1, page_size: int = 20
    ) -> tuple[int, List[Dict[str, Any]]]:
        """특정 사용자의 추천 로그 조회 (페이지네이션)"""
        try:
            query = {"user_id": user_id}
            total = self.recommendations_collection.count_documents(query)

            skip = (page - 1) * page_size
            cursor = (
                self.recommendations_collection.find(query)
                .sort("recommended_at", -1)
                .skip(skip)
                .limit(page_size)
            )

            items = list(cursor)
            return total, items

        except PyMongoError as e:
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
        except PyMongoError as e:
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

            result = self.interactions_collection.update_one(
                {"recommendation_id": recommendation_id},
                {
                    "$set": doc,
                    "$setOnInsert": {"created_at": datetime.utcnow()},
                },
                upsert=True,
            )

            saved_doc = self.interactions_collection.find_one(
                {"recommendation_id": recommendation_id}
            )
            return saved_doc

        except PyMongoError as e:
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
        except PyMongoError as e:
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
        except PyMongoError as e:
            logger.error(f"Failed to log event: {e}")
            return None

    def log_session_context(
        self,
        user_id: int,
        session_id: str,
        context_data: Dict[str, Any],
    ) -> str:
        """
        세션 컨텍스트 로깅 (RL 메타데이터 1번만 저장).
        
        Args:
            user_id: 사용자 ID
            session_id: 세션 ID
            context_data: RL 메타데이터 (candidates, candidates_features, candidates_scores, final_display)
        """
        event_doc = {
            "user_id": user_id,
            "paper_id": "",
            "activity_type": "session_context",
            "timestamp": datetime.utcnow(),
            "session_id": session_id,
            "metadata": context_data,
        }

        try:
            result = self.events_collection.insert_one(event_doc)
            logger.info(f"Logged session context for session {session_id}")
            return str(result.inserted_id)
        except PyMongoError as e:
            logger.error(f"Failed to log session context: {e}")
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
                .sort("timestamp", 1)
                .skip(skip)
                .limit(page_size)
            )

            items = list(cursor)
            return total, items

        except PyMongoError as e:
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
                .sort("timestamp", -1)
                .skip(skip)
                .limit(page_size)
            )

            items = list(cursor)
            return total, items

        except PyMongoError as e:
            logger.error(f"Failed to get events for user {user_id}: {e}")
            return 0, []

    def get_user_context_stats(self, user_id: int) -> Dict[str, float]:
        """
        RL 모델 입력을 위한 사용자 컨텍스트 통계 계산.
        
        Returns:
            dict: {
                "activity_count": 최근 30일 활동 수,
                "avg_dwell_time": 평균 체류 시간 (초),
                "bookmark_rate": 북마크 비율 (0.0 ~ 1.0)
            }
        """
        try:
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            activity_count = self.events_collection.count_documents({
                "user_id": user_id,
                "timestamp": {"$gte": thirty_days_ago}
            })

            pipeline = [
                {
                    "$match": {
                        "user_id": user_id,
                        "activity_type": "detail_view",
                        "metadata.dwell_time_ms": {"$exists": True}
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "avg_dwell_ms": {"$avg": "$metadata.dwell_time_ms"}
                    }
                }
            ]
            avg_dwell_result = list(self.events_collection.aggregate(pipeline))
            avg_dwell_time = (avg_dwell_result[0]["avg_dwell_ms"] / 1000.0) if avg_dwell_result else 0.0

            total_interactions = self.events_collection.count_documents({"user_id": user_id})
            bookmark_count = self.events_collection.count_documents({
                "user_id": user_id,
                "activity_type": "bookmark"
            })
            bookmark_rate = (bookmark_count / total_interactions) if total_interactions > 0 else 0.0

            return {
                "activity_count": float(activity_count),
                "avg_dwell_time": float(avg_dwell_time),
                "bookmark_rate": float(bookmark_rate),
            }

        except PyMongoError as e:
            logger.error(f"Failed to calculate user context stats for {user_id}: {e}")
            return {
                "activity_count": 0.0,
                "avg_dwell_time": 0.0,
                "bookmark_rate": 0.0,
            }


