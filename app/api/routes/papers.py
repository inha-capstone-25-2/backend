from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from app.db.connection import get_mongo_collection_for_search  # 변경

router = APIRouter(prefix="/papers", tags=["papers"])

class Paper(BaseModel):
    _id: str
    id: Optional[str] = None
    title: Optional[str] = None
    abstract: Optional[str] = None
    authors: Optional[str] = None
    categories: Optional[str] = None
    update_date: Optional[str] = None

@router.get("/search", response_model=List[Paper])
def search_papers(
    q: str = Query(..., min_length=1, description="검색어"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    client, coll = get_mongo_collection_for_search()  # 변경: prod 검색용 커넥션
    if coll is None:
        raise HTTPException(status_code=500, detail="Mongo collection unavailable")

    try:
        regex = {"$regex": q, "$options": "i"}
        query = {"$or": [{"title": regex}, {"abstract": regex}, {"authors": regex}]}
        projection = {
            "_id": 1,
            "id": 1,
            "title": 1,
            "abstract": 1,
            "authors": 1,
            "categories": 1,
            "update_date": 1,
        }

        cursor = coll.find(query, projection).skip(offset).limit(limit)
        items = []
        for doc in cursor:
            doc["_id"] = str(doc.get("_id"))
            items.append(doc)
        return items
    finally:
        if client:
            client.close()