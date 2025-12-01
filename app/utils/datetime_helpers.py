"""
DateTime 변환 유틸리티 함수.

MongoDB 문서의 datetime 필드를 ISO 문자열로 변환하는 헬퍼 함수들을 제공합니다.
"""

from typing import Dict, List, Any
from datetime import datetime


def convert_datetime_to_iso(value: Any) -> str | None:
    """
    datetime 객체를 ISO 형식 문자열로 변환.

    Args:
        value: 변환할 값 (datetime 객체 또는 기타)

    Returns:
        ISO 형식 문자열 또는 None
    """
    if value and hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def convert_datetime_fields(doc: Dict[str, Any], fields: List[str]) -> None:
    """
    MongoDB 문서의 지정된 datetime 필드들을 ISO 문자열로 변환.

    Args:
        doc: 변환할 문서 (딕셔너리)
        fields: 변환할 필드 이름 리스트
    """
    for field in fields:
        if field in doc and hasattr(doc[field], "isoformat"):
            doc[field] = doc[field].isoformat()
