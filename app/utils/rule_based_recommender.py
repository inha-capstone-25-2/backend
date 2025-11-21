"""
룰 베이스 추천 시스템 메인 모듈.

사용자에게 맞춤 논문을 추천합니다.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Any
from datetime import datetime
import logging
from pymongo.database import Database
from sqlalchemy.orm import Session

from app.utils.rule_based_scorer import RuleBasedScorer
from app.core.settings import settings

if TYPE_CHECKING:
    from app.models.user import User

logger = logging.getLogger(__name__)


class RuleBasedRecommender:
    """룰 베이스 추천 시스템"""
    
    # 점수 가중치
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
        top_k: int = 10,
        candidate_limit: int = 100
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
        # 1. 사용자 관심 카테고리 가져오기
        user_interests = self._get_user_interests(user, db_postgres)
        if not user_interests:
            logger.info(f"User {user.id} has no interests. Using popular papers.")
        
        # 2. 사용자 활동 이력 가져오기
        viewed_paper_ids, activity_categories = self._get_user_activity(user.id, db_mongo)
        
        # 3. 후보 논문 가져오기
        candidate_papers = self._get_candidate_papers(
            db_mongo, 
            user_interests, 
            viewed_paper_ids,
            candidate_limit
        )
        
        if not candidate_papers:
            logger.warning(f"No candidate papers found for user {user.id}")
            return []
        
        # 4. 각 논문에 대해 점수 계산
        recommendations = []
        
        for paper in candidate_papers:
            paper_id = str(paper.get("_id"))
            paper_categories = paper.get("categories", [])
            
            # 각 점수 계산
            interest_score = self.scorer.calculate_interest_score(user_interests, paper)
            popularity_score = self.scorer.calculate_popularity_score(paper)
            recency_score = self.scorer.calculate_recency_score(paper)
            personalization_score = self.scorer.calculate_personalization_score(
                user.id,
                paper_id,
                paper_categories,
                viewed_paper_ids,
                activity_categories
            )
            
            # 최종 점수 (가중 평균)
            total_score = (
                interest_score * self.WEIGHT_INTEREST +
                popularity_score * self.WEIGHT_POPULARITY +
                recency_score * self.WEIGHT_RECENCY +
                personalization_score * self.WEIGHT_PERSONALIZATION
            )
            
            # 추천 이유 분석
            reasons = self._analyze_recommendation_reasons(
                interest_score,
                popularity_score,
                personalization_score
            )
            
            recommendations.append({
                "paper": paper,
                "paper_id": paper_id,
                "total_score": total_score,
                "breakdown": {
                    "interest_score": interest_score,
                    "popularity_score": popularity_score,
                    "recency_score": recency_score,
                    "personalization_score": personalization_score
                },
                "reasons": reasons
            })
        
        # 5. 점수 기준 정렬 및 상위 k개 선택
        recommendations.sort(key=lambda x: x["total_score"], reverse=True)
        return recommendations[:top_k]
    
    def _get_user_interests(self, user: User, db: Session) -> List[str]:
        """사용자 관심 카테고리 코드 리스트 반환"""
        from app.models.category import Category
        from app.models.user_interest import UserInterest
        
        # user.interests를 직접 사용하면 DetachedInstanceError 발생
        # (캐시된 User 객체는 세션에서 분리되어 있음)
        # 따라서 UserInterest를 직접 쿼리
        user_interest_objs = db.query(UserInterest).filter(
            UserInterest.user_id == user.id
        ).all()
        
        if not user_interest_objs:
            return []
        
        category_ids = [ui.category_id for ui in user_interest_objs]
        categories = db.query(Category).filter(Category.id.in_(category_ids)).all()
        return [cat.code for cat in categories]
    
    def _get_user_activity(self, user_id: int, db: Database) -> tuple[List[str], List[str]]:
        """
        사용자 활동 이력 분석.
        
        Returns:
            (viewed_paper_ids, activity_categories)
        """
        activities = db["user_activities"].find(
            {"user_id": user_id, "activity_type": "view"},
            {"paper_id": 1, "metadata": 1}
        ).sort("timestamp", -1).limit(50)  # 최근 50개만
        
        viewed_paper_ids = []
        activity_categories = []
        
        for activity in activities:
            paper_id = activity.get("paper_id")
            if paper_id:
                viewed_paper_ids.append(str(paper_id))
            
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
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        추천 후보 논문 가져오기.
        
        관심사와 관련된 논문 + 인기 논문 혼합
        """
        collection = db[settings.mongo_collection]
        
        candidates = []
        
        # 1. 관심사 관련 논문 (limit의 70%)
        if user_interests:
            interest_papers = list(collection.find(
                {"categories": {"$in": user_interests}},
                limit=int(limit * 0.7)
            ))
            candidates.extend(interest_papers)
        
        # 2. 인기 논문 (limit의 30%)
        popular_papers = list(collection.find(
            {},
            sort=[("view_count", -1), ("bookmark_count", -1)],
            limit=int(limit * 0.3)
        ))
        candidates.extend(popular_papers)
        
        # 3. 중복 제거 (_id 기준)
        seen_ids = set()
        unique_candidates = []
        for paper in candidates:
            paper_id = paper.get("_id")
            if paper_id not in seen_ids:
                seen_ids.add(paper_id)
                unique_candidates.append(paper)
        
        return unique_candidates[:limit]
    
    def _analyze_recommendation_reasons(
        self,
        interest_score: float,
        popularity_score: float,
        personalization_score: float
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
