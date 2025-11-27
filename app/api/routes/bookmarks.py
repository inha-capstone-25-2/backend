from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List
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
from app.utils.mongodb import safe_object_id
from app.services.bookmark_service import BookmarkService

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])


@router.post("", response_model=BookmarkOut, status_code=status.HTTP_201_CREATED)
def create_bookmark(
    payload: BookmarkCreate,
    current_user: User = Depends(get_current_user),
    db: Database = Depends(get_mongo_db),
):
    """북마크 생성."""
    service = BookmarkService(db)
    
    try:
        doc = service.create_bookmark(
            user=current_user,
            doi=payload.doi,
            notes=payload.notes
        )
        return BookmarkOut(**doc)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )


@router.get("", response_model=BookmarkListOut)
def list_bookmarks(
    current_user: User = Depends(get_current_user),
    doi: str | None = Query(None, description="특정 논문 북마크만 조회 (DOI)"),
    db: Database = Depends(get_mongo_db),
):
    """북마크 목록 조회."""
    service = BookmarkService(db)
    items = service.list_bookmarks(user=current_user, doi=doi)
    
    bookmark_items = [
        BookmarkOut(
            id=doc["id"],
            user_id=doc["user_id"],
            doi=doc["doi"],
            bookmarked_at=doc["bookmarked_at"],
            notes=doc.get("notes"),
        )
        for doc in items
    ]
    
    return BookmarkListOut(items=bookmark_items)


@router.put("/{bookmark_id}", response_model=BookmarkOut)
def update_bookmark(
    bookmark_id: str,
    payload: BookmarkUpdate,
    current_user: User = Depends(get_current_user),
    db: Database = Depends(get_mongo_db),
):
    """북마크 수정 (notes 필드만 수정 가능)."""
    obj_id = safe_object_id(bookmark_id, "bookmark ID")
    service = BookmarkService(db)
    
    try:
        result = service.update_bookmark(
            user=current_user,
            bookmark_id=obj_id,
            notes=payload.notes
        )
        return BookmarkOut(
            id=result["id"],
            user_id=result["user_id"],
            doi=result["doi"],
            bookmarked_at=result["bookmarked_at"],
            notes=result.get("notes"),
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )


@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bookmark(
    bookmark_id: str,
    current_user: User = Depends(get_current_user),
    db: Database = Depends(get_mongo_db),
):
    """북마크 삭제."""
    obj_id = safe_object_id(bookmark_id, "bookmark ID")
    service = BookmarkService(db)
    
    try:
        service.delete_bookmark(user=current_user, bookmark_id=obj_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )
    
    return