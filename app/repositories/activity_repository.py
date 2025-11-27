import logging
from typing import Dict, Any, List

from pymongo.database import Database
from pymongo.collection import Collection

from app.core.constants import COLLECTION_USER_ACTIVITIES
from app.utils.mongodb import transform_id_field

logger = logging.getLogger(__name__)


class ActivityRepository:
    def __init__(self, db: Database):
        self.db = db
        self.activities_collection: Collection = db[COLLECTION_USER_ACTIVITIES]

    def get_activities(
        self,
        user_id: int | None,
        activity_type: str | None,
        doi: str | None,
        limit: int,
    ) -> tuple[int, List[Dict[str, Any]]]:
        """활동 로그 조회 (total count, items 반환)"""
        query = {}
        if user_id is not None:
            query["user_id"] = user_id
        if activity_type:
            query["activity_type"] = activity_type
        if doi:
            query["doi"] = doi

        total = self.activities_collection.count_documents(query)
        cursor = (
            self.activities_collection.find(query).sort("timestamp", -1).limit(limit)
        )

        items = []
        for doc in cursor:
            transform_id_field(doc)
            # metadata가 없으면 None으로 설정
            if "metadata" not in doc:
                doc["metadata"] = None
            items.append(doc)

        return total, items
