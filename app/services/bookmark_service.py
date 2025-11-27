import logging
from typing import Dict, Any, List
from bson import ObjectId

from pymongo.database import Database

from app.repositories.bookmark_repository import BookmarkRepository
from app.utils.activity_logger import log_activity
from app.models.user import User

logger = logging.getLogger(__name__)

from app.core.exceptions import ResourceNotFoundException, DuplicateResourceException


class BookmarkService:
    def __init__(self, db: Database):
        self.db = db
        self.repo = BookmarkRepository(db)

    def create_bookmark(
        self, user: User, doi: str, notes: str | None
    ) -> Dict[str, Any]:
        """북마크 생성 및 활동 로그"""

        # 1. 논문 존재 확인
        if not self.repo.paper_exists(doi):
            raise ResourceNotFoundException("Paper", doi)

        # 2. 중복 확인
        existing = self.repo.find_by_user_and_doi(user.id, doi)
        if existing:
            raise DuplicateResourceException("Bookmark")

        # 3. 북마크 생성
        doc = self.repo.create_bookmark(user.id, doi, notes)

        # 4. 활동 로그
        log_activity(db=self.db, user_id=user.id, activity_type="bookmark", doi=doi)

        return doc

    def list_bookmarks(
        self, user: User, doi: str | None = None
    ) -> List[Dict[str, Any]]:
        """북마크 목록 조회"""
        return self.repo.list_bookmarks(user.id, doi)

    def update_bookmark(
        self, user: User, bookmark_id: ObjectId, notes: str | None
    ) -> Dict[str, Any] | None:
        """북마크 수정"""
        result = self.repo.update_bookmark(bookmark_id, user.id, notes)

        if not result:
            raise ResourceNotFoundException("Bookmark", str(bookmark_id))

        return result

    def delete_bookmark(self, user: User, bookmark_id: ObjectId) -> None:
        """북마크 삭제 및 활동 로그"""

        # 1. 삭제 전 문서 조회 (활동 로그용)
        doc = self.repo.delete_bookmark(bookmark_id, user.id)

        if not doc:
            raise ResourceNotFoundException("Bookmark", str(bookmark_id))

        # 2. 활동 로그
        log_activity(
            db=self.db, user_id=user.id, activity_type="unbookmark", doi=doc["doi"]
        )
