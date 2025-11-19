from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
import math
from app.db.mongodb import get_mongo_collection_for_search

router = APIRouter(prefix="/papers", tags=["papers"])

class Paper(BaseModel):
    _id: str
    id: Optional[str] = None
    title: Optional[str] = None
    abstract: Optional[str] = None
    authors: Optional[str] = None
    categories: Optional[List[str]] = None
    update_date: Optional[str] = None

class PaperSearchResponse(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool
    items: List[Paper]

@router.get("/search", response_model=PaperSearchResponse)
def search_papers(
    q: Optional[str] = Query(None, min_length=1, description="검색어"),
    categories: Optional[List[str]] = Query(None, description="카테고리 코드(복수 선택 가능)"),
    page: int = Query(1, ge=1, description="페이지 (1부터)"),
):
    client, coll = get_mongo_collection_for_search()
    if coll is None:
        raise HTTPException(status_code=500, detail="Mongo collection unavailable")

    try:
        query = {}
        if q:
            regex = {"$regex": q, "$options": "i"}
            query["$or"] = [{"title": regex}, {"abstract": regex}, {"authors": regex}]
        if categories:
            query["categories"] = {"$in": categories}

        projection = {
            "_id": 1,
            "id": 1,
            "title": 1,
            "abstract": 1,
            "authors": 1,
            "categories": 1,
            "update_date": 1,
        }

        page_size = 10
        skip = (page - 1) * page_size

        total = coll.count_documents(query)
        total_pages = max(1, math.ceil(total / page_size)) if total else 0

        cursor = coll.find(query, projection).skip(skip).limit(page_size)
        items = []
        for doc in cursor:
            doc["_id"] = str(doc.get("_id"))
            items.append(doc)

        return {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "items": items,
        }
    finally:
        if client:
            client.close()