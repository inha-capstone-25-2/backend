"""북마크 저장소 모듈.

사용자 북마크의 CRUD 연산을 담당합니다.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from pymongo.database import Database
from pymongo.collection import Collection
from bson import ObjectId

from app.core.settings import settings
from app.core.constants import COLLECTION_BOOKMARKS
from app.utils.mongodb import transform_id_field

logger = logging.getLogger(__name__)


class BookmarkRepository:
    """북마크 저장소.

    Attributes:
        db: MongoDB 데이터베이스 인스턴스.
        bookmarks_collection: 북마크 컬렉션.
        papers_collection: 논문 컬렉션.
    """

    def __init__(self, db: Database):
        """인스턴스를 초기화한다.

        Args:
            db: MongoDB 데이터베이스 인스턴스.
        """
        self.db = db
        self.bookmarks_collection: Collection = db[COLLECTION_BOOKMARKS]
        self.papers_collection: Collection = db[settings.mongo_collection]

    def paper_exists(self, doi: str) -> bool:
        """논문 존재 여부를 확인한다.

        Args:
            doi: 논문 ID.

        Returns:
            논문이 존재하면 True.
        """
        doc = self.papers_collection.find_one({"_id": doi}, {"_id": 1})
        return doc is not None

    def find_by_user_and_doi(self, user_id: int, doi: str) -> Dict[str, Any] | None:
        """사용자 ID와 DOI로 북마크를 조회한다.

        Args:
            user_id: 사용자 ID.
            doi: 논문 ID.

        Returns:
            북마크 문서 또는 None.
        """
        doc = self.bookmarks_collection.find_one({"user_id": user_id, "doi": doi})
        return doc

    def create_bookmark(
        self, user_id: int, doi: str, notes: str | None
    ) -> Dict[str, Any]:
        """북마크를 생성한다.

        Args:
            user_id: 사용자 ID.
            doi: 논문 ID.
            notes: 북마크 메모.

        Returns:
            생성된 북마크 문서.
        """
        doc = {
            "user_id": user_id,
            "doi": doi,
            "bookmarked_at": datetime.utcnow(),
            "notes": notes,
        }
        result = self.bookmarks_collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        transform_id_field(doc)
        return doc

    def list_bookmarks(
        self, user_id: int, doi: str | None = None
    ) -> List[Dict[str, Any]]:
        """북마크 목록을 조회한다.

        Args:
            user_id: 사용자 ID.
            doi: 논문 ID 필터.

        Returns:
            북마크 문서 리스트.
        """
        query = {"user_id": user_id}
        if doi:
            query["doi"] = doi

        pipeline = [
            {"$match": query},
            {"$sort": {"bookmarked_at": -1}},
            {
                "$lookup": {
                    "from": self.papers_collection.name,
                    "localField": "doi",
                    "foreignField": "_id",
                    "as": "paper_info",
                }
            },
            {
                "$unwind": {
                    "path": "$paper_info",
                    "preserveNullAndEmptyArrays": True,
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "user_id": 1,
                    "doi": 1,
                    "bookmarked_at": 1,
                    "notes": 1,
                    "journal_ref": "$paper_info.journal_ref",
                }
            },
        ]

        cursor = self.bookmarks_collection.aggregate(pipeline)
        items = []
        for doc in cursor:
            transform_id_field(doc)
            items.append(doc)

        return items

    def update_bookmark(
        self, bookmark_id: ObjectId, user_id: int, notes: str | None
    ) -> Dict[str, Any] | None:
        """북마크를 수정한다.

        Args:
            bookmark_id: 북마크 ID.
            user_id: 사용자 ID.
            notes: 업데이트할 메모.

        Returns:
            업데이트된 북마크 문서 또는 None.
        """
        result = self.bookmarks_collection.find_one_and_update(
            {"_id": bookmark_id, "user_id": user_id},
            {"$set": {"notes": notes, "bookmarked_at": datetime.utcnow()}},
            return_document=True,
        )

        if result:
            transform_id_field(result)

        return result

    def delete_bookmark(
        self, bookmark_id: ObjectId, user_id: int
    ) -> Dict[str, Any] | None:
        """북마크를 삭제한다.

        Args:
            bookmark_id: 북마크 ID.
            user_id: 사용자 ID.

        Returns:
            삭제된 북마크 문서 또는 None.
        """
        doc = self.bookmarks_collection.find_one(
            {"_id": bookmark_id, "user_id": user_id}
        )

        if doc:
            self.bookmarks_collection.delete_one(
                {"_id": bookmark_id, "user_id": user_id}
            )

        return doc
