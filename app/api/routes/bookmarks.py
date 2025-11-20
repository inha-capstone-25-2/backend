from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List
from datetime import datetime
from pymongo.database import Database

from app.db.mongodb import get_mongo_db
from app.api.deps import get_current_user
from app.models.user import User
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
    paper_oid = safe_object_id(payload.paper_id, "paper ID")
    
    doc = {
        "user_id": current_user.id,
        "paper_id": paper_oid,
        "bookmarked_at": datetime.utcnow(),
        "notes": payload.notes,
    }
    result = db["bookmarks"].insert_one(doc)
    doc["_id"] = result.inserted_id
    
    # API 응답용으로 변환: _id → id, ObjectId → 문자열
    serialize_object_id(doc, "_id", "paper_id")
    doc["id"] = doc.pop("_id")
    
    # 북마크 활동 로그
    log_activity(
        db=db,
        user_id=current_user.id,
        activity_type="bookmark",
        paper_id=payload.paper_id
    )
    
    return BookmarkOut(**doc)


@router.get("", response_model=BookmarkListOut)
def list_bookmarks(
    current_user: User = Depends(get_current_user),
    paper_id: str | None = Query(None, description="특정 논문 북마크만 조회"),
    db: Database = Depends(get_mongo_db),
):
    query = {"user_id": current_user.id}
    if paper_id:
        query["paper_id"] = safe_object_id(paper_id, "paper ID")
    
    cursor = db["bookmarks"].find(query).sort("bookmarked_at", -1)
    items = []
    for doc in cursor:
        serialize_object_id(doc, "_id", "paper_id")
        doc["id"] = doc.pop("_id")
        items.append(BookmarkOut(
            id=doc["id"],
            user_id=doc["user_id"],
            paper_id=doc["paper_id"],
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
    
    serialize_object_id(result, "_id", "paper_id")
    result["id"] = result.pop("_id")
    
    return BookmarkOut(
        id=result["id"],
        user_id=result["user_id"],
        paper_id=result["paper_id"],
        bookmarked_at=result["bookmarked_at"],
        notes=result.get("notes"),
    )


@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bookmark(
    bookmark_id: str,
    current_user: User = Depends(get_current_user),
    db: Database = Depends(get_mongo_db),
):
    obj_id = safe_object_id(bookmark_id, "bookmark ID")
    
    # 삭제 전에 paper_id 조회 (활동 로그용)
    bookmark_doc = db["bookmarks"].find_one({"_id": obj_id, "user_id": current_user.id})
    if not bookmark_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )
    
    result = db["bookmarks"].delete_one({"_id": obj_id, "user_id": current_user.id})
    
    # 북마크 취소 활동 로그
    if result.deleted_count > 0:
        log_activity(
            db=db,
            user_id=current_user.id,
            activity_type="unbookmark",
            paper_id=str(bookmark_doc["paper_id"])
        )
    
    return