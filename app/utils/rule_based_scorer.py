"""
룰 베이스 추천 시스템의 점수 계산 모듈.

사용자와 논문 간의 다양한 점수를 계산합니다:
- Interest Score: 관심사 매칭
- Popularity Score: 인기도
- Recency Score: 최신성
- Personalization Score: 개인화
"""
from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Any
from datetime import datetime, timedelta
import logging

if TYPE_CHECKING:
    from app.models.user import User

logger = logging.getLogger(__name__)


class RuleBasedScorer:
    """룰 베이스 점수 계산기"""
    
    @staticmethod
    def calculate_interest_score(
        user_interests: List[str],  # 사용자 관심 카테고리 코드 리스트
        paper: Dict[str, Any]
    ) -> float:
        """
        관심사 기반 점수 계산.
        
        Args:
            user_interests: 사용자 관심 카테고리 코드 리스트
            paper: 논문 문서 (MongoDB document)
        
        Returns:
            관심사 점수 (0.0 이상)
        """
        score = 0.0
        
        paper_categories = paper.get("categories", [])
        paper_keywords = paper.get("keywords", [])
        paper_title = paper.get("title", "").lower()
        
        for interest_code in user_interests:
            # 카테고리 직접 매칭 (가장 높은 점수)
            if interest_code in paper_categories:
                score += 3.0
            
            # 키워드 매칭 (중간 점수)
            # 카테고리 코드가 키워드에 포함되어 있을 수 있음
            interest_lower = interest_code.lower()
            for keyword in paper_keywords:
                if interest_lower in keyword.lower() or keyword.lower() in interest_lower:
                    score += 2.0
                    break  # 중복 가산 방지
            
            # 제목에 카테고리 코드 포함 (낮은 점수)
            if interest_lower in paper_title:
                score += 1.0
        
        return score
    
    @staticmethod
    def calculate_popularity_score(paper: Dict[str, Any]) -> float:
        """
        인기도 기반 점수 계산.
        
        Args:
            paper: 논문 문서 (MongoDB document)
        
        Returns:
            인기도 점수 (0.0 이상)
        """
        score = 0.0
        
        # view_count 가중치
        view_count = paper.get("view_count", 0)
        score += view_count * 0.001
        
        # bookmark_count 가중치 (북마크가 조회보다 더 강한 관심 표시)
        bookmark_count = paper.get("bookmark_count", 0)
        score += bookmark_count * 0.005
        
        return score
    
    @staticmethod
    def calculate_recency_score(paper: Dict[str, Any]) -> float:
        """
        최신성 기반 점수 계산.
        
        Args:
            paper: 논문 문서 (MongoDB document)
        
        Returns:
            최신성 점수 (0.0 ~ 10.0)
        """
        update_date_str = paper.get("update_date")
        
        if not update_date_str:
            return 1.0  # 날짜 정보 없으면 기본 점수
        
        try:
            # update_date는 "YYYY-MM-DD" 형식
            update_date = datetime.strptime(update_date_str, "%Y-%m-%d")
            now = datetime.now()
            
            # 날짜 차이 (일 단위)
            days_old = (now - update_date).days
            
            # 최신일수록 높은 점수
            # 1년 이내: 10.0 ~ 5.0
            # 2년 이내: 5.0 ~ 2.0
            # 그 이상: 1.0
            if days_old < 0:
                days_old = 0  # 미래 날짜 방어
            
            if days_old <= 365:
                score = 10.0 - (days_old / 365) * 5.0
            elif days_old <= 730:
                score = 5.0 - ((days_old - 365) / 365) * 3.0
            else:
                score = 1.0
            
            return max(score, 1.0)
        
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse update_date: {update_date_str}, error: {e}")
            return 1.0
    
    @staticmethod
    def calculate_personalization_score(
        user_id: int,
        paper_id: str,
        paper_categories: List[str],
        viewed_paper_ids: List[str],
        user_activity_categories: List[str]
    ) -> float:
        """
        개인화 점수 계산.
        
        Args:
            user_id: 사용자 ID
            paper_id: 논문 ID (문자열)
            paper_categories: 논문 카테고리 리스트
            viewed_paper_ids: 사용자가 본 논문 ID 리스트
            user_activity_categories: 사용자가 본 논문들의 카테고리 리스트 (중복 포함)
        
        Returns:
            개인화 점수 (음수 가능)
        """
        score = 0.0
        
        # 이미 본 논문은 추천하지 않음 (큰 감점)
        if paper_id in viewed_paper_ids:
            score -= 10.0
        
        # 사용자가 자주 본 카테고리와 매칭 (가점)
        for category in paper_categories:
            if category in user_activity_categories:
                score += 1.0  # 본 적 있는 카테고리면 관심 있다고 판단
        
        return score
