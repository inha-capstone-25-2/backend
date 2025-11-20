from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from pymongo.database import Database
from app.db.mongodb import get_mongo_db
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])

class BookmarkCreate(BaseModel):
    paper_id: str = Field(..., description="MongoDB papers._id")
    notes: Optional[str] = None

class BookmarkOut(BaseModel):
    id: str
    user_id: int
    paper_id: str
    bookmarked_at: datetime
    notes: Optional[str] = None

@router.post("", response_model=BookmarkOut, status_code=status.HTTP_201_CREATED)
def create_bookmark(
    payload: BookmarkCreate,
    current_user: User = Depends(get_current_user),
    db: Database = Depends(get_mongo_db),
):
    doc = {
        "user_id": current_user.id,
        "paper_id": ObjectId(payload.paper_id),
        "bookmarked_at": datetime.utcnow(),
        "notes": payload.notes,
    }
    result = db["bookmarks"].insert_one(doc)
    doc["_id"] = result.inserted_id
    doc["id"] = str(result.inserted_id)
    doc["paper_id"] = str(doc["paper_id"])
    return BookmarkOut(**doc)

class BookmarkListOut(BaseModel):
    items: List[BookmarkOut]

@router.get("", response_model=BookmarkListOut)
def list_bookmarks(
    current_user: User = Depends(get_current_user),
    paper_id: Optional[str] = Query(None, description="특정 논문 북마크만 조회"),
    db: Database = Depends(get_mongo_db),
):
    query = {"user_id": current_user.id}
    if paper_id:
        query["paper_id"] = ObjectId(paper_id)
    cursor = db["bookmarks"].find(query).sort("bookmarked_at", -1)
    items = []
    for doc in cursor:
        doc["id"] = str(doc["_id"])
        doc["paper_id"] = str(doc["paper_id"])
        items.append(BookmarkOut(
            id=doc["id"],
            user_id=doc["user_id"],
            paper_id=doc["paper_id"],
            bookmarked_at=doc["bookmarked_at"],
            notes=doc.get("notes"),
        ))
    return BookmarkListOut(items=items)

class BookmarkUpdate(BaseModel):
    notes: Optional[str] = None

@router.put("/{bookmark_id}", response_model=BookmarkOut)
def update_bookmark(
    bookmark_id: str,
    payload: BookmarkUpdate,
    current_user: User = Depends(get_current_user),
    db: Database = Depends(get_mongo_db),
):
    try:
        obj_id = ObjectId(bookmark_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid bookmark_id"
        )
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
    result["id"] = str(result["_id"])
    result["paper_id"] = str(result["paper_id"])
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
    try:
        obj_id = ObjectId(bookmark_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid bookmark_id"
        )
    result = db["bookmarks"].delete_one({"_id": obj_id, "user_id": current_user.id})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )
    return