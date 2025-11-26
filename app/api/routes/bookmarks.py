from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List
from datetime import datetime
from pymongo.database import Database

from app.db.mongodb import get_mongo_db
from app.api.deps import get_current_user
from app.models.user import User
from app.core.settings import settings
from app.schemas.bookmark import (
    BookmarkCreate,
    BookmarkOut,
    BookmarkUpdate,
    BookmarkListOut,
)
from app.utils.mongodb import safe_object_id, serialize_object_id
from app.utils.activity_logger import log_activity

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])


@router.post("", response_model=BookmarkOut, status_code=status.HTTP_201_CREATED)
def create_bookmark(
    payload: BookmarkCreate,
    current_user: User = Depends(get_current_user),
    db: Database = Depends(get_mongo_db),
):
    """
    북마크 생성.
    
    doi는 논문의 id(doi) 필드를 사용합니다.
    MongoDB papers 컬렉션에서 해당 doi로 논문이 존재하는지 확인합니다.
    """
    # doi로 논문 존재 여부 확인 (_id는 이제 arXiv ID)
    papers_coll = db[settings.mongo_collection]
    paper_doc = papers_coll.find_one({"_id": payload.doi}, {"_id": 1})
    if not paper_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper not found with doi: {payload.doi}"
        )
    
    # 중복 북마크 확인
    existing = db["bookmarks"].find_one({
        "user_id": current_user.id,
        "doi": payload.doi
    })
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bookmark already exists for this paper"
        )
    
    doc = {
        "user_id": current_user.id,
        "doi": payload.doi,
        "bookmarked_at": datetime.utcnow(),
        "notes": payload.notes,
    }
    result = db["bookmarks"].insert_one(doc)
    doc["_id"] = result.inserted_id
    
    # _id를 문자열로 변환하고 id로 변경
    serialize_object_id(doc, "_id")
    doc["id"] = doc.pop("_id")
    
    # 북마크 활동 로그 (doi 전달)
    log_activity(
        db=db,
        user_id=current_user.id,
        activity_type="bookmark",
        doi=payload.doi
    )
    
    return BookmarkOut(**doc)


@router.get("", response_model=BookmarkListOut)
def list_bookmarks(
    current_user: User = Depends(get_current_user),
    doi: str | None = Query(None, description="특정 논문 북마크만 조회 (DOI)"),
    db: Database = Depends(get_mongo_db),
):
    """
    북마크 목록 조회.
    
    doi로 필터링할 경우 논문의 id(doi)를 사용합니다.
    """
    query = {"user_id": current_user.id}
    if doi:
        query["doi"] = doi
    
    cursor = db["bookmarks"].find(query).sort("bookmarked_at", -1)
    items = []
    for doc in cursor:
        serialize_object_id(doc, "_id")
        doc["id"] = doc.pop("_id")
        items.append(BookmarkOut(
            id=doc["id"],
            user_id=doc["user_id"],
            doi=doc["doi"],
            bookmarked_at=doc["bookmarked_at"],
            notes=doc.get("notes"),
        ))
    return BookmarkListOut(items=items)


@router.put("/{bookmark_id}", response_model=BookmarkOut)
def update_bookmark(
    bookmark_id: str,
    payload: BookmarkUpdate,
    current_user: User = Depends(get_current_user),
    db: Database = Depends(get_mongo_db),
):
    """
    북마크 수정 (notes 필드만 수정 가능).
    
    bookmark_id는 북마크 문서의 _id (MongoDB ObjectId)입니다.
    """
    obj_id = safe_object_id(bookmark_id, "bookmark ID")
    
    # 본인 북마크만 수정 가능
    result = db["bookmarks"].find_one_and_update(
        {"_id": obj_id, "user_id": current_user.id},
        {"$set": {"notes": payload.notes, "bookmarked_at": datetime.utcnow()}},
        return_document=True,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )
    
    serialize_object_id(result, "_id")
    result["id"] = result.pop("_id")
    
    return BookmarkOut(
        id=result["id"],
        user_id=result["user_id"],
        doi=result["doi"],
        bookmarked_at=result["bookmarked_at"],
        notes=result.get("notes"),
    )


@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bookmark(
    bookmark_id: str,
    current_user: User = Depends(get_current_user),
    db: Database = Depends(get_mongo_db),
):
    """
    북마크 삭제.
    
    bookmark_id는 북마크 문서의 _id (MongoDB ObjectId)입니다.
    """
    obj_id = safe_object_id(bookmark_id, "bookmark ID")
    
    # 삭제 전에 doi 조회 (활동 로그용)
    bookmark_doc = db["bookmarks"].find_one({"_id": obj_id, "user_id": current_user.id})
    if not bookmark_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )
    
    result = db["bookmarks"].delete_one({"_id": obj_id, "user_id": current_user.id})
    
    # 북마크 취소 활동 로그 (doi 전달)
    if result.deleted_count > 0:
        log_activity(
            db=db,
            user_id=current_user.id,
            activity_type="unbookmark",
            doi=bookmark_doc["doi"]
        )
    
    return