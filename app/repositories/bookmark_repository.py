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
    def __init__(self, db: Database):
        self.db = db
        self.bookmarks_collection: Collection = db[COLLECTION_BOOKMARKS]
        self.papers_collection: Collection = db[settings.mongo_collection]

    def paper_exists(self, doi: str) -> bool:
        """논문 존재 여부 확인"""
        doc = self.papers_collection.find_one({"_id": doi}, {"_id": 1})
        return doc is not None

    def find_by_user_and_doi(self, user_id: int, doi: str) -> Dict[str, Any] | None:
        """사용자 ID와 DOI로 북마크 조회"""
        doc = self.bookmarks_collection.find_one({
            "user_id": user_id,
            "doi": doi
        })
        return doc

    def create_bookmark(
        self,
        user_id: int,
        doi: str,
        notes: str | None
    ) -> Dict[str, Any]:
        """북마크 생성"""
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
        self,
        user_id: int,
        doi: str | None = None
    ) -> List[Dict[str, Any]]:
        """북마크 목록 조회"""
        query = {"user_id": user_id}
        if doi:
            query["doi"] = doi
        
        cursor = self.bookmarks_collection.find(query).sort("bookmarked_at", -1)
        items = []
        for doc in cursor:
            transform_id_field(doc)
            items.append(doc)
        
        return items

    def update_bookmark(
        self,
        bookmark_id: ObjectId,
        user_id: int,
        notes: str | None
    ) -> Dict[str, Any] | None:
        """북마크 수정"""
        result = self.bookmarks_collection.find_one_and_update(
            {"_id": bookmark_id, "user_id": user_id},
            {"$set": {"notes": notes, "bookmarked_at": datetime.utcnow()}},
            return_document=True,
        )
        
        if result:
            transform_id_field(result)
        
        return result

    def delete_bookmark(
        self,
        bookmark_id: ObjectId,
        user_id: int
    ) -> Dict[str, Any] | None:
        """북마크 삭제 (삭제 전 문서 반환)"""
        doc = self.bookmarks_collection.find_one({
            "_id": bookmark_id,
            "user_id": user_id
        })
        
        if doc:
            self.bookmarks_collection.delete_one({
                "_id": bookmark_id,
                "user_id": user_id
            })
        
        return doc
