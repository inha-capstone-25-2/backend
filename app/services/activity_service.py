import logging
from typing import Dict, Any, List

from pymongo.database import Database

from app.repositories.activity_repository import ActivityRepository

logger = logging.getLogger(__name__)


class ActivityService:
    def __init__(self, db: Database):
        self.db = db
        self.repo = ActivityRepository(db)

    def get_activities(
        self,
        user_id: int | None,
        activity_type: str | None,
        doi: str | None,
        limit: int,
    ) -> Dict[str, Any]:
        """활동 로그 조회"""
        total, items = self.repo.get_activities(user_id, activity_type, doi, limit)

        return {"total": total, "items": items}
