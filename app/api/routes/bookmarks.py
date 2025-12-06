"""북마크 API 라우터 모듈.

사용자 북마크 CRUD 엔드포인트를 정의합니다.
"""

from fastapi import APIRouter, Depends, status, Query
from typing import List
from pymongo.database import Database

from app.db.mongodb import get_mongo_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.bookmark import (
    BookmarkCreate,
    BookmarkOut,
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

    doc = service.create_bookmark(
        user=current_user, doi=payload.doi, notes=payload.notes
    )
    return BookmarkOut(**doc)


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



@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bookmark(
    bookmark_id: str,
    current_user: User = Depends(get_current_user),
    db: Database = Depends(get_mongo_db),
):
    """북마크 삭제."""
    obj_id = safe_object_id(bookmark_id, "bookmark ID")
    service = BookmarkService(db)

    service.delete_bookmark(user=current_user, bookmark_id=obj_id)

    return
