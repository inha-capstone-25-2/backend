"""논문 서비스 모듈.

논문 검색, 상세 조회, 검색 기록 등의 비즈니스 로직을 담당합니다.
"""

import logging
from typing import List, Dict, Any

from pymongo.database import Database
from elasticsearch import Elasticsearch

from app.repositories.paper_repository import PaperRepository
from app.utils.activity_logger import log_activity
from app.models.user import User
from app.core.constants import DEFAULT_PAGE_SIZE
from app.core.exceptions import ResourceNotFoundException

logger = logging.getLogger(__name__)


class PaperService:
    """논문 서비스.

    Attributes:
        db: MongoDB 데이터베이스 인스턴스.
        repo: 논문 저장소 인스턴스.
    """

    def __init__(self, db: Database, es_client: Elasticsearch | None = None):
        """인스턴스를 초기화한다.

        Args:
            db: MongoDB 데이터베이스 인스턴스.
            es_client: Elasticsearch 클라이언트 (옵션).
        """
        self.db = db
        self.repo = PaperRepository(db, es_client)

    def search_papers(
        self,
        user: User,
        q: str | None,
        categories: List[str] | None,
        page: int,
        sort_by: str,
    ) -> Dict[str, Any]:
        """논문 검색 및 기록 저장 (캐싱 제거됨)"""

        result = self.repo.search_papers(
            q=q,
            categories=categories,
            page=page,
            page_size=DEFAULT_PAGE_SIZE,
            sort_by=sort_by,
        )

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

        doc = self.repo.get_paper_and_increment_view(paper_id)

        if not doc:
            raise ResourceNotFoundException("Paper", paper_id)

        log_activity(db=self.db, user_id=user.id, activity_type="view", doi=paper_id)

        return doc
