import logging
from typing import List, Dict, Any

from pymongo.database import Database

from app.repositories.paper_repository import PaperRepository
from app.utils.activity_logger import log_activity
from app.models.user import User
from app.core.constants import DEFAULT_PAGE_SIZE
from app.core.exceptions import ResourceNotFoundException
from app.core.cache import (
    get_cached_search_result,
    cache_search_result,
)

logger = logging.getLogger(__name__)


class PaperService:
    def __init__(self, db: Database):
        self.db = db
        self.repo = PaperRepository(db)

    def search_papers(
        self,
        user: User,
        q: str | None,
        categories: List[str] | None,
        page: int,
        sort_by: str,
    ) -> Dict[str, Any]:
        """논문 검색 및 기록 저장 (캐싱 적용)"""

        # 1. 캐시 확인
        cached_result = get_cached_search_result(q, categories, page, sort_by)
        if cached_result is not None:
            result = cached_result
        else:
            # 2. 캐시 미스 - 검색 수행
            result = self.repo.search_papers(
                q=q,
                categories=categories,
                page=page,
                page_size=DEFAULT_PAGE_SIZE,
                sort_by=sort_by,
            )

            # 3. 결과 캐싱
            cache_search_result(q, categories, page, sort_by, result)

        # 4. 검색 기록 및 활동 로그 저장 (캐시와 무관하게 항상 저장)
        if q or categories:
            self.repo.save_search_history(
                user_id=user.id,
                query=q,
                categories=categories,
                result_count=result["total"],
            )

            log_activity(
                db=self.db,
                user_id=user.id,
                activity_type="search",
                metadata={
                    "search_query": q,
                    "categories": categories,
                    "result_count": result["total"],
                },
            )

        return result

    def get_search_history(self, user_id: int | None, limit: int) -> Dict[str, Any]:
        """검색 기록 조회"""
        return self.repo.get_search_history(user_id=user_id, limit=limit)

    def get_viewed_papers(self, user: User, page: int, limit: int) -> Dict[str, Any]:
        """내가 본 논문 조회"""
        return self.repo.get_viewed_papers(user_id=user.id, page=page, limit=limit)

    def get_paper_detail(self, user: User, paper_id: str) -> Dict[str, Any]:
        """논문 상세 조회 및 활동 로그"""

        # 1. 논문 조회 및 조회수 증가
        doc = self.repo.get_paper_and_increment_view(paper_id)

        if not doc:
            raise ResourceNotFoundException("Paper", paper_id)

        # 2. 활동 로그 기록
        log_activity(db=self.db, user_id=user.id, activity_type="view", doi=paper_id)

        return doc
