"""
MongoDB 관련 유틸리티 함수.

ObjectId 변환, 문서 직렬화 등 MongoDB 작업에 필요한 공통 함수를 제공합니다.
"""

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException, status
from typing import Any, Dict


def safe_object_id(id_str: str, field_name: str = "ID") -> ObjectId:
    """
    문자열을 안전하게 ObjectId로 변환.
    
    유효하지 않은 ObjectId 형식인 경우 HTTPException을 발생시킵니다.
    
    Args:
        id_str: 변환할 문자열 ID
        field_name: 에러 메시지에 표시할 필드 이름 (기본: "ID")
    
    Returns:
        ObjectId: 변환된 ObjectId 객체
    
    Raises:
        HTTPException: 유효하지 않은 ObjectId 형식인 경우 (HTTP 400)
    
    Example:
        >>> oid = safe_object_id("507f1f77bcf86cd799439011", "paper ID")
        >>> oid = safe_object_id(paper_id, "bookmark ID")
    """
    try:
        return ObjectId(id_str)
    except (InvalidId, Exception):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name} format"
        )


def serialize_object_id(doc: Dict[str, Any], *fields: str) -> Dict[str, Any]:
    """
    MongoDB 문서의 ObjectId 필드를 문자열로 변환.
    
    지정된 필드들의 ObjectId를 문자열로 변환합니다.
    필드가 지정되지 않으면 "_id"만 변환합니다.
    원본 문서를 수정하며, 체이닝을 위해 문서를 반환합니다.
    
    Args:
        doc: MongoDB 문서 (딕셔너리)
        *fields: 변환할 필드 이름들 (기본: "_id")
    
    Returns:
        Dict[str, Any]: 변환된 문서 (원본 수정됨)
    
    Example:
        >>> doc = {"_id": ObjectId(...), "paper_id": ObjectId(...)}
        >>> serialize_object_id(doc, "_id", "paper_id")
        {"_id": "507f...", "paper_id": "507f..."}
        
        >>> serialize_object_id(doc)  # _id만 변환
        {"_id": "507f...", "paper_id": ObjectId(...)}
    """
    if not fields:
        fields = ("_id",)
    
    for field in fields:
        if field in doc and doc[field] is not None:
            doc[field] = str(doc[field])
    
    return doc


def serialize_doc_for_api(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    MongoDB 문서를 API 응답용으로 직렬화.
    
    - "_id"를 "id"로 변경하고 문자열로 변환
    - 일반적인 ObjectId 필드들(paper_id 등)도 문자열로 변환
    
    Args:
        doc: MongoDB 문서
    
    Returns:
        Dict[str, Any]: API 응답용으로 직렬화된 문서
    
    Example:
        >>> doc = {"_id": ObjectId(...), "paper_id": ObjectId(...), "title": "..."}
        >>> serialize_doc_for_api(doc)
        {"id": "507f...", "paper_id": "507f...", "title": "..."}
    """
    if "_id" in doc:
        doc["id"] = str(doc["_id"])
    
    # 일반적인 ObjectId 필드들 자동 변환
    for field in ["paper_id", "user_id", "category_id", "bookmark_id"]:
        if field in doc and isinstance(doc[field], ObjectId):
            doc[field] = str(doc[field])
    
    return doc
