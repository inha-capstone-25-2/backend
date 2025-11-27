"""
사용자 활동 로깅 유틸리티.

사용자의 다양한 활동(view, bookmark, search 등)을 MongoDB에 기록합니다.
"""

from pymongo.database import Database
from datetime import datetime
import logging
from typing import Dict, Any, Optional
from app.core.constants import COLLECTION_USER_ACTIVITIES


logger = logging.getLogger(__name__)


def log_activity(
    db: Database,
    user_id: int,
    activity_type: str,
    doi: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    사용자 활동을 MongoDB user_activities 컬렉션에 기록.
    
    Args:
        db: MongoDB Database 객체
        user_id: 사용자 ID
        activity_type: 활동 타입 (view, bookmark, search, click 등)
        doi: 논문 DOI/arXiv ID (선택, search 등은 없음)
        metadata: 추가 메타데이터 (선택)
    
    Example:
        >>> log_activity(
        ...     db=db,
        ...     user_id=123,
        ...     activity_type="view",
        ...     doi="0704.0775"
        ... )
        
        >>> log_activity(
        ...     db=db,
        ...     user_id=123,
        ...     activity_type="search",
        ...     metadata={"search_query": "transformer", "result_count": 42}
        ... )
    """
    activity_doc = {
        "user_id": user_id,
        "activity_type": activity_type,
        "metadata": metadata or {},
        "timestamp": datetime.utcnow(),
    }
    
    # doi가 있으면 문자열 그대로 저장
    if doi:
        activity_doc["doi"] = doi
    
    try:
        db[COLLECTION_USER_ACTIVITIES].insert_one(activity_doc)
        logger.debug(f"Activity logged: {activity_type} for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to log activity: {e}")
        # 활동 로그 실패는 주요 기능에 영향 주지 않음
