from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List
import math
from pymongo.database import Database
from bson import ObjectId
from bson.errors import InvalidId

from app.db.mongodb import get_mongo_db
from app.core.settings import settings
from app.schemas.paper import Paper, PaperSearchResponse

router = APIRouter(prefix="/papers", tags=["papers"])


@router.get("/search", response_model=PaperSearchResponse)
def search_papers(
    q: str | None = Query(None, min_length=1, description="검색어"),
    categories: List[str] | None = Query(None, description="카테고리 코드(복수 선택 가능)"),
    page: int = Query(1, ge=1, description="페이지 (1부터)"),
    db: Database = Depends(get_mongo_db),
):
    coll = db[settings.mongo_collection]

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


@router.get("/{paper_id}", response_model=Paper)
def get_paper(
    paper_id: str,
    db: Database = Depends(get_mongo_db),
):
    coll = db[settings.mongo_collection]

    try:
        oid = ObjectId(paper_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid paper ID format")

    doc = coll.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Paper not found")

    doc["_id"] = str(doc["_id"])
    return doc