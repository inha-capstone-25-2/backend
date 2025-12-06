"""활동 서비스 모듈.

사용자 활동 로그의 비즈니스 로직을 담당합니다.
"""

import logging
from typing import Dict, Any, List

from pymongo.database import Database

from app.repositories.activity_repository import ActivityRepository

logger = logging.getLogger(__name__)


class ActivityService:
    """사용자 활동 서비스.

    Attributes:
        db: MongoDB 데이터베이스 인스턴스.
        repo: 활동 저장소 인스턴스.
    """

    def __init__(self, db: Database):
        """인스턴스를 초기화한다.

        Args:
            db: MongoDB 데이터베이스 인스턴스.
        """
        self.db = db
        self.repo = ActivityRepository(db)

    def get_activities(
        self,
        user_id: int | None,
        activity_type: str | None,
        doi: str | None,
        limit: int,
    ) -> Dict[str, Any]:
        """활동 로그를 조회한다.

        Args:
            user_id: 사용자 ID (None이면 전체 조회).
            activity_type: 활동 유형 필터.
            doi: 논문 ID 필터.
            limit: 조회 제한 개수.

        Returns:
            total과 items를 포함한 딕셔너리.
        """
        total, items = self.repo.get_activities(user_id, activity_type, doi, limit)

        return {"total": total, "items": items}
