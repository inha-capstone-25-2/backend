"""북마크 서비스 모듈.

사용자 북마크의 비즈니스 로직을 담당합니다.
"""

import logging
from typing import Dict, Any, List
from bson import ObjectId

from pymongo.database import Database

from app.repositories.bookmark_repository import BookmarkRepository
from app.utils.activity_logger import log_activity
from app.models.user import User
from app.core.exceptions import ResourceNotFoundException, DuplicateResourceException

logger = logging.getLogger(__name__)


class BookmarkService:
    """북마크 서비스.

    Attributes:
        db: MongoDB 데이터베이스 인스턴스.
        repo: 북마크 저장소 인스턴스.
    """

    def __init__(self, db: Database):
        """인스턴스를 초기화한다.

        Args:
            db: MongoDB 데이터베이스 인스턴스.
        """
        self.db = db
        self.repo = BookmarkRepository(db)

    def create_bookmark(
        self, user: User, doi: str, notes: str | None
    ) -> Dict[str, Any]:
        """북마크를 생성한다.

        Args:
            user: 사용자 객체.
            doi: 논문 ID.
            notes: 북마크 메모.

        Returns:
            생성된 북마크 문서.

        Raises:
            ResourceNotFoundException: 논문이 존재하지 않는 경우.
            DuplicateResourceException: 이미 북마크가 존재하는 경우.
        """
        if not self.repo.paper_exists(doi):
            raise ResourceNotFoundException("Paper", doi)

        existing = self.repo.find_by_user_and_doi(user.id, doi)
        if existing:
            raise DuplicateResourceException("Bookmark")

        doc = self.repo.create_bookmark(user.id, doi, notes)
        log_activity(db=self.db, user_id=user.id, activity_type="bookmark", doi=doi)

        return doc

    def list_bookmarks(
        self, user: User, doi: str | None = None
    ) -> List[Dict[str, Any]]:
        """북마크 목록을 조회한다.

        Args:
            user: 사용자 객체.
            doi: 논문 ID 필터.

        Returns:
            북마크 문서 리스트.
        """
        return self.repo.list_bookmarks(user.id, doi)

    def update_bookmark(
        self, user: User, bookmark_id: ObjectId, notes: str | None
    ) -> Dict[str, Any] | None:
        """북마크를 수정한다.

        Args:
            user: 사용자 객체.
            bookmark_id: 북마크 ID.
            notes: 업데이트할 메모.

        Returns:
            업데이트된 북마크 문서.

        Raises:
            ResourceNotFoundException: 북마크가 존재하지 않는 경우.
        """
        result = self.repo.update_bookmark(bookmark_id, user.id, notes)

        if not result:
            raise ResourceNotFoundException("Bookmark", str(bookmark_id))

        return result

    def delete_bookmark(self, user: User, bookmark_id: ObjectId) -> None:
        """북마크를 삭제한다.

        Args:
            user: 사용자 객체.
            bookmark_id: 북마크 ID.

        Raises:
            ResourceNotFoundException: 북마크가 존재하지 않는 경우.
        """
        doc = self.repo.delete_bookmark(bookmark_id, user.id)

        if not doc:
            raise ResourceNotFoundException("Bookmark", str(bookmark_id))

        log_activity(
            db=self.db, user_id=user.id, activity_type="unbookmark", doi=doc["doi"]
        )
