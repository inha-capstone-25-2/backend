"""
룰 베이스 추천 시스템 메인 모듈.

사용자에게 맞춤 논문을 추천합니다.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Any
from datetime import datetime
import logging
import time
from pymongo.database import Database
from sqlalchemy.orm import Session
from app.core.constants import COLLECTION_USER_ACTIVITIES


from app.utils.rule_based_scorer import RuleBasedScorer
from app.core.settings import settings

if TYPE_CHECKING:
    from app.models.user import User

logger = logging.getLogger(__name__)


class RuleBasedRecommender:
    """룰 베이스 추천 시스템"""

    WEIGHT_INTEREST = 0.4
    WEIGHT_POPULARITY = 0.2
    WEIGHT_RECENCY = 0.1
    WEIGHT_PERSONALIZATION = 0.3

    def __init__(self):
        self.scorer = RuleBasedScorer()

    def recommend(
        self,
        user: User,
        db_postgres: Session,
        db_mongo: Database,
        top_k: int = None,  # None이면 전체 반환
        candidate_limit: int = 50,  # 100 -> 50으로 축소
    ) -> List[Dict[str, Any]]:
        """
        룰 베이스 추천 실행.

        Args:
            user: 사용자 모델 (PostgreSQL)
            db_postgres: PostgreSQL 세션
            db_mongo: MongoDB Database
            top_k: 반환할 추천 개수
            candidate_limit: 후보 논문 개수 (성능 최적화)

        Returns:
            추천 결과 리스트 (각 항목은 paper, scores, reasons 포함)
        """
        start_time = time.time()
        
        step_start = time.time()
        user_interests = self._get_user_interests(user, db_postgres)
        logger.info(f"[PERF] Get user interests took {time.time() - step_start:.3f}s")
        if not user_interests:
            logger.info(f"User {user.id} has no interests. Using popular papers.")

        step_start = time.time()
        viewed_paper_ids, activity_categories = self._get_user_activity(
            user.id, db_mongo
        )
        logger.info(f"[PERF] Get user activity took {time.time() - step_start:.3f}s")

        step_start = time.time()
        candidate_papers = self._get_candidate_papers(
            db_mongo, user_interests, viewed_paper_ids, candidate_limit
        )
        logger.info(f"[PERF] Get candidate papers ({len(candidate_papers)} papers) took {time.time() - step_start:.3f}s")

        if not candidate_papers:
            logger.warning(f"No candidate papers found for user {user.id}")
            return []

        step_start = time.time()
        recommendations = []

        for paper in candidate_papers:
            paper_id = str(paper.get("_id"))
            paper_categories = paper.get("categories", [])

            interest_score = self.scorer.calculate_interest_score(user_interests, paper)
            popularity_score = self.scorer.calculate_popularity_score(paper)
            recency_score = self.scorer.calculate_recency_score(paper)
            personalization_score = self.scorer.calculate_personalization_score(
                user.id,
                paper_id,
                paper_categories,
                viewed_paper_ids,
                activity_categories,
            )

            total_score = (
                interest_score * self.WEIGHT_INTEREST
                + popularity_score * self.WEIGHT_POPULARITY
                + recency_score * self.WEIGHT_RECENCY
                + personalization_score * self.WEIGHT_PERSONALIZATION
            )

            reasons = self._analyze_recommendation_reasons(
                interest_score, popularity_score, personalization_score
            )

            recommendations.append(
                {
                    "paper": paper,
                    "paper_id": paper_id,
                    "total_score": total_score,
                    "breakdown": {
                        "interest_score": interest_score,
                        "popularity_score": popularity_score,
                        "recency_score": recency_score,
                        "personalization_score": personalization_score,
                    },
                    "reasons": reasons,
                }
            )
        
        logger.info(f"[PERF] Score calculation took {time.time() - step_start:.3f}s")

        step_start = time.time()
        recommendations.sort(key=lambda x: x["total_score"], reverse=True)
        
        # top_k가 지정된 경우에만 슬라이싱 (None이면 전체 반환)
        if top_k is not None:
            results = recommendations[:top_k]
        else:
            results = recommendations
            
        logger.info(f"[PERF] Sorting and filtering took {time.time() - step_start:.3f}s")
        
        logger.info(f"[PERF] Total recommendation time: {time.time() - start_time:.3f}s")
        return results

    def _get_user_interests(self, user: User, db: Session) -> List[str]:
        """사용자 관심 카테고리 코드 리스트 반환"""
        from app.models.category import Category
        from app.models.user_interest import UserInterest

        # user.interests를 직접 사용하면 DetachedInstanceError 발생
        # (캐시된 User 객체는 세션에서 분리되어 있음)
        # 따라서 UserInterest를 직접 쿼리
        user_interest_objs = (
            db.query(UserInterest).filter(UserInterest.user_id == user.id).all()
        )

        if not user_interest_objs:
            return []

        category_ids = [ui.category_id for ui in user_interest_objs]
        categories = db.query(Category).filter(Category.id.in_(category_ids)).all()
        return [cat.code for cat in categories]

    def _get_user_activity(
        self, user_id: int, db: Database
    ) -> tuple[List[str], List[str]]:
        """
        사용자 활동 이력 분석.

        Returns:
            (viewed_paper_ids, activity_categories)
        """
        # Projection: 필요한 필드만 선택
        activities = (
            db[COLLECTION_USER_ACTIVITIES]
            .find(
                {"user_id": user_id, "activity_type": "view"},
                {"doi": 1, "metadata.categories": 1},  # 필요한 필드만
            )
            .sort("timestamp", -1)
            .limit(50)
        )  # 최근 50개만

        viewed_paper_ids = []
        activity_categories = []

        for activity in activities:
            doi = activity.get("doi")
            if doi:
                viewed_paper_ids.append(str(doi))

            # metadata에 카테고리 정보가 있을 수 있음
            metadata = activity.get("metadata", {})
            categories = metadata.get("categories", [])
            activity_categories.extend(categories)

        return viewed_paper_ids, activity_categories

    def _get_candidate_papers(
        self,
        db: Database,
        user_interests: List[str],
        viewed_paper_ids: List[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """
        추천 후보 논문 가져오기.

        관심사와 관련된 논문 + 인기 논문 혼합
        """
        collection = db[settings.mongo_collection]

        # Projection: 필요한 필드만 선택 (abstract 제외하여 성능 개선)
        projection = {
            "_id": 1,
            "title": 1,
            "categories": 1,
            "keywords": 1,
            "view_count": 1,
            "bookmark_count": 1,
            "update_date": 1,
            "difficulty_level": 1,
            "authors": 1,
            "authors": 1,
            "journal_ref": 1,
            # abstract는 크기가 크므로 제외 (응답 시 필요하지 않음)
        }

        # 최적화된 쿼리: 하나의 쿼리로 통합
        # 관심사가 있으면 관심사 기반, 없으면 인기 논문만
        if user_interests:
            # 관심사 카테고리에 해당하는 논문을 인기도 순으로 정렬
            # 인덱스 활용: categories 인덱스 + view_count/bookmark_count 복합 인덱스
            candidates = list(
                collection.find(
                    {"categories": {"$in": user_interests}},
                    projection,
                )
                .sort([("view_count", -1), ("bookmark_count", -1)])
                .limit(limit)
            )
        else:
            # 관심사가 없으면 전체에서 인기 논문만
            candidates = list(
                collection.find(
                    {},
                    projection,
                )
                .sort([("view_count", -1), ("bookmark_count", -1)])
                .limit(limit)
            )

        return candidates

    def _analyze_recommendation_reasons(
        self,
        interest_score: float,
        popularity_score: float,
        personalization_score: float,
    ) -> List[str]:
        """추천 이유 분석"""
        reasons = []

        if interest_score > 3.0:
            reasons.append("관심사와 높은 관련성")
        elif interest_score > 1.0:
            reasons.append("관심사와 일부 관련성")

        if popularity_score > 2.0:
            reasons.append("인기 논문")
        elif popularity_score > 0.5:
            reasons.append("주목받는 논문")

        if personalization_score > 1.0:
            reasons.append("개인 취향과 일치")

        return reasons if reasons else ["다양한 주제의 논문"]
