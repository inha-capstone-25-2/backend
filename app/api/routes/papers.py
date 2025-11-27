from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List
import math
import logging
from datetime import datetime
from pymongo.database import Database
from app.core.constants import COLLECTION_SEARCH_HISTORY, COLLECTION_USER_ACTIVITIES


from app.db.mongodb import get_mongo_db
from app.core.settings import settings
from app.schemas.paper import (
    Paper,
    PaperSearchResponse,
    SearchHistoryResponse,
    SearchHistoryItem,
    SearchHistoryFilters,
)
from app.utils.mongodb import serialize_object_id
from app.utils.activity_logger import log_activity
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/papers", tags=["papers"])
logger = logging.getLogger(__name__)


def save_search_history(
    db: Database,
    user_id: int,
    query: str | None,
    categories: List[str] | None,
    result_count: int
) -> None:
    """
    검색 기록을 MongoDB에 저장.
    
    Args:
        db: MongoDB Database 객체
        user_id: 사용자 ID
        query: 검색어
        categories: 카테고리 필터
        result_count: 검색 결과 개수
    """
    history_doc = {
        "user_id": user_id,
        "query": query or "",
        "filters": {
            "categories": categories or []
        },
        "result_count": result_count,
        "searched_at": datetime.utcnow()
    }
    
    try:
        db[COLLECTION_SEARCH_HISTORY].insert_one(history_doc)
        logger.debug(f"Search history saved for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to save search history: {e}")
        # 검색 기록 저장 실패는 검색 자체에 영향 주지 않음


@router.get("/search", response_model=PaperSearchResponse)
def search_papers(
    q: str | None = Query(None, min_length=1, description="검색어"),
    categories: List[str] | None = Query(None, description="카테고리 코드(복수 선택 가능)"),
    page: int = Query(1, ge=1, description="페이지 (1부터)"),
    sort_by: str = Query("relevance", description="정렬 기준: relevance(관련도), view_count(조회수), update_date(최신순)"),
    db: Database = Depends(get_mongo_db),
    current_user: User = Depends(get_current_user),  # 인증 필수
):
    coll = db[settings.mongo_collection]
    
    # 디버그: 어떤 컬렉션을 사용하는지 로깅
    logger.info(f"[DEBUG] Using database: {db.name}, collection: {settings.mongo_collection}")
    logger.info(f"[DEBUG] Collection full name: {coll.full_name}")

    query = {}
    use_text_search = False
    
    # Text Search 사용 (단어 기반 전문 검색)
    if q:
        query["$text"] = {"$search": q}
        use_text_search = True
    
    if categories:
        query["categories"] = {"$in": categories}

    # Projection 설정: 리스트 뷰용 (성능 최적화)
    # abstract는 크기가 크므로 제외 (상세 페이지에서만 조회)
    projection = {
        "_id": 1,
        "id": 1,
        "title": 1,
        "authors": 1,
        "categories": 1,
        "update_date": 1,
        "view_count": 1,
    }
    
    # Text Search 사용 시 관련도 점수 추가
    if use_text_search:
        projection["score"] = {"$meta": "textScore"}

    page_size = 10
    skip = (page - 1) * page_size

    # Count 계산: 근사치 전략 (성능 최적화)
    CANDIDATE_LIMIT = 2000
    is_approximate = False
    items = []
    total = 0
    
    if use_text_search:
        # Text Search 최적화: Two-Step 전략
        try:
            # Step 1: Text Search로 후보군 ID와 Score만 먼저 가져옴
            candidates_cursor = coll.find(
                {"$text": {"$search": q}},
                {"score": {"$meta": "textScore"}}
            ).limit(CANDIDATE_LIMIT)
            
            candidates = []
            for doc in candidates_cursor:
                candidates.append({"_id": doc["_id"], "score": doc.get("score", 0)})
            
            # Step 2: 카테고리 필터링 및 데이터 조회
            if not candidates:
                total = 0
                items = []
            else:
                candidate_ids = [c["_id"] for c in candidates]
                
                filter_query = {"_id": {"$in": candidate_ids}}
                if categories:
                    filter_query["categories"] = {"$in": categories}
                    
                data_projection = projection.copy()
                if "score" in data_projection:
                    del data_projection["score"]
                
                docs_cursor = coll.find(filter_query, data_projection)
                docs_map = {doc["_id"]: doc for doc in docs_cursor}
                
                # Step 3: 결과 조합 및 정렬
                final_items = []
                for cand in candidates:
                    if cand["_id"] in docs_map:
                        doc = docs_map[cand["_id"]]
                        doc["score"] = cand["score"]
                        final_items.append(doc)
                
                # 정렬 수행
                if sort_by == "view_count":
                    final_items.sort(key=lambda x: x.get("view_count", 0), reverse=True)
                elif sort_by == "update_date":
                    final_items.sort(key=lambda x: x.get("update_date", ""), reverse=True)
                else:  # relevance
                    final_items.sort(key=lambda x: x["score"], reverse=True)
                
                total = len(final_items)
                is_approximate = True
                
                # Step 4: 페이징
                start = skip
                end = skip + page_size
                items = final_items[start:end]
                
                # score 제거 및 _id를 id로 변환
                for item in items:
                    if "_id" in item:
                        item["id"] = str(item.pop("_id"))
                    item.pop("score", None)
            
        except Exception as e:
            logger.error(f"[Search] Two-step search failed: {e}")
            raise HTTPException(status_code=500, detail="Search operation failed")
            
    else:
        # 일반 쿼리
        total = coll.count_documents(query, limit=10000)
        if total >= 10000:
            is_approximate = True
            
        # 정렬 기준 설정
        if sort_by == "view_count":
            sort_field = [("view_count", -1), ("update_date", -1)]
        elif sort_by == "update_date":
            sort_field = [("update_date", -1)]
        else:
            sort_field = [("update_date", -1)]
        
        cursor = coll.find(query, projection).sort(sort_field).skip(skip).limit(page_size)
        for doc in cursor:
            if "_id" in doc:
                doc["id"] = str(doc.pop("_id"))
            items.append(doc)
    
    total_pages = max(1, math.ceil(total / page_size)) if total else 0

    # 검색 기록 저장
    if q or categories:
        save_search_history(
            db=db,
            user_id=current_user.id,
            query=q,
            categories=categories,
            result_count=total
        )
        
        log_activity(
            db=db,
            user_id=current_user.id,
            activity_type="search",
            metadata={
                "search_query": q,
                "categories": categories,
                "result_count": total
            }
        )

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
        "is_approximate": is_approximate,
        "items": items,
    }


@router.get("/search-history", response_model=SearchHistoryResponse)
def get_search_history(
    user_id: int | None = Query(None, description="사용자 ID로 필터링"),
    limit: int = Query(100, ge=1, le=1000, description="조회할 기록 수"),
    db: Database = Depends(get_mongo_db),
):
    """
    검색 기록 조회 (인증 불필요).
    """
    collection = db[COLLECTION_SEARCH_HISTORY]
    
    query = {}
    if user_id is not None:
        query["user_id"] = user_id
    
    total = collection.count_documents(query)
    cursor = collection.find(query).sort("searched_at", -1).limit(limit)
    
    items = []
    for doc in cursor:
        serialize_object_id(doc)
        doc["id"] = doc.pop("_id")
        doc.setdefault("user_id", None)
        doc.setdefault("filters", None)
        doc.setdefault("result_count", None)
        items.append(SearchHistoryItem(**doc))
    
    return SearchHistoryResponse(total=total, items=items)


@router.get("/viewed", response_model=PaperSearchResponse)
def get_viewed_papers(
    page: int = Query(1, ge=1, description="페이지 (1부터)"),
    limit: int = Query(10, ge=1, le=100, description="페이지당 항목 수"),
    db: Database = Depends(get_mongo_db),
    current_user: User = Depends(get_current_user),
):
    """
    현재 로그인한 사용자가 조회한 논문 목록을 반환.
    
    user_activities 컬렉션에서 해당 사용자의 'view' 활동을 조회하고,
    해당 논문들의 정보를 papers 컬렉션에서 가져와 반환합니다.
    최신 조회 순으로 정렬되며, 중복 제거됩니다.
    """
    activities_coll = db[COLLECTION_USER_ACTIVITIES]
    papers_coll = db[settings.mongo_collection]
    
    query = {
        "user_id": current_user.id,
        "activity_type": "view"
    }
    
    # MongoDB aggregation을 사용하여 중복 제거 및 최신순 정렬
    # user_activities 컬렉션의 doi 필드 사용
    pipeline = [
        {"$match": query},
        {"$sort": {"timestamp": -1}},
        {"$group": {
            "_id": "$doi",  # paper_id -> doi
            "last_viewed": {"$first": "$timestamp"}
        }},
        {"$sort": {"last_viewed": -1}},
        {"$skip": (page - 1) * limit},
        {"$limit": limit}
    ]
    
    viewed_papers = list(activities_coll.aggregate(pipeline))
    
    # 전체 개수 조회
    count_pipeline = [
        {"$match": query},
        {"$group": {"_id": "$doi"}},  # paper_id -> doi
        {"$count": "total"}
    ]
    count_result = list(activities_coll.aggregate(count_pipeline))
    total = count_result[0]["total"] if count_result else 0
    
    paper_ids = [item["_id"] for item in viewed_papers if item["_id"]]
    
    items = []
    if paper_ids:
        paper_docs = papers_coll.find(
            {"_id": {"$in": paper_ids}},
            {
                "_id": 1,
                "id": 1,
                "title": 1,
                "authors": 1,
                "categories": 1,
                "update_date": 1,
                "view_count": 1,
            }
        )
        
        papers_map = {doc["_id"]: doc for doc in paper_docs}
        
        for viewed in viewed_papers:
            paper_id = viewed["_id"]
            if paper_id in papers_map:
                doc = papers_map[paper_id]
                if "_id" in doc:
                    doc["id"] = str(doc.pop("_id"))
                items.append(doc)
    
    page_size = limit
    total_pages = max(1, math.ceil(total / page_size)) if total else 0
    
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
        "is_approximate": False,
        "items": items,
    }


@router.get("/{paper_id}", response_model=Paper)
def get_paper(
    paper_id: str,
    db: Database = Depends(get_mongo_db),
    current_user: User = Depends(get_current_user),
):
    """
    논문 상세 정보 조회.
    
    조회 시 해당 논문의 view_count를 자동으로 1 증가시킵니다.
    사용자 활동 로그도 함께 기록됩니다.
    """
    coll = db[settings.mongo_collection]

    # paper_id는 이제 arXiv ID (문자열)이므로 직접 사용
    # view_count 증가 + 문서 조회 (원자적 연산)
    doc = coll.find_one_and_update(
        {"_id": paper_id},
        {"$inc": {"view_count": 1}},
        return_document=True  # 업데이트 후 문서 반환
    )
    
    if not doc:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    # 사용자 활동 로그 기록
    log_activity(
        db=db,
        user_id=current_user.id,
        activity_type="view",
        doi=paper_id  # paper_id -> doi
    )

    # _id를 id로 변환
    serialize_object_id(doc)
    doc["id"] = doc.pop("_id")
    return doc