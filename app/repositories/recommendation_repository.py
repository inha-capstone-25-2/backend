import logging
from datetime import datetime, timedelta
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
        
        # session_id 추가 (있는 경우에만)
        if session_id:
            log_doc["session_id"] = session_id

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
            # 1. 최근 30일 활동 수 (user_activities 컬렉션 가정)
            # 현재 user_activities 컬렉션 접근이 없으므로 events_collection으로 대체하거나 추가 필요
            # 여기서는 recommendation_events 기준으로 계산
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            activity_count = self.events_collection.count_documents({
                "user_id": user_id,
                "timestamp": {"$gte": thirty_days_ago}
            })

            # 2. 평균 체류 시간 (detail_view 이벤트의 dwell_time_ms)
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

            # 3. 북마크 비율 (북마크 수 / 전체 상호작용 수)
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

        except Exception as e:
            logger.error(f"Failed to calculate user context stats for {user_id}: {e}")
            return {
                "activity_count": 0.0,
                "avg_dwell_time": 0.0,
                "bookmark_rate": 0.0,
            }


