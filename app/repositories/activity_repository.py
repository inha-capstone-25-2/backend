"""사용자 활동 저장소 모듈.

사용자 활동 로그의 조회를 담당합니다.
"""

import logging
from typing import Dict, Any, List

from pymongo.database import Database
from pymongo.collection import Collection

from app.core.constants import COLLECTION_USER_ACTIVITIES
from app.utils.mongodb import transform_id_field

logger = logging.getLogger(__name__)


class ActivityRepository:
    """사용자 활동 로그 저장소.

    Attributes:
        db: MongoDB 데이터베이스 인스턴스.
        activities_collection: 활동 로그 컬렉션.
    """

    def __init__(self, db: Database):
        """인스턴스를 초기화한다.

        Args:
            db: MongoDB 데이터베이스 인스턴스.
        """
        self.db = db
        self.activities_collection: Collection = db[COLLECTION_USER_ACTIVITIES]

    def get_activities(
        self,
        user_id: int | None,
        activity_type: str | None,
        doi: str | None,
        limit: int,
    ) -> tuple[int, List[Dict[str, Any]]]:
        """활동 로그를 조회한다.

        Args:
            user_id: 사용자 ID (None이면 전체 조회).
            activity_type: 활동 유형 필터.
            doi: 논문 ID 필터.
            limit: 조회 제한 개수.

        Returns:
            (total count, items) 튜플.
        """
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
            if "metadata" not in doc:
                doc["metadata"] = None
            items.append(doc)

        return total, items
