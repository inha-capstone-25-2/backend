from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List
import math
import logging
from datetime import datetime
from pymongo.database import Database

from app.db.mongodb import get_mongo_db
from app.core.settings import settings
from app.schemas.paper import (
    Paper,
    PaperSearchResponse,
    SearchHistoryResponse,
    SearchHistoryItem,
    SearchHistoryFilters,
)
from app.utils.mongodb import safe_object_id, serialize_object_id
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
        db["search_history"].insert_one(history_doc)
        logger.debug(f"Search history saved for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to save search history: {e}")
        # 검색 기록 저장 실패는 검색 자체에 영향 주지 않음


@router.get("/search", response_model=PaperSearchResponse)
def search_papers(
    q: str | None = Query(None, min_length=1, description="검색어"),
    categories: List[str] | None = Query(None, description="카테고리 코드(복수 선택 가능)"),
    page: int = Query(1, ge=1, description="페이지 (1부터)"),
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
        # "abstract": 1,  # 리스트 뷰에서는 제외 (네트워크 최적화)
        "authors": 1,
        "categories": 1,
        "update_date": 1,
    }
    
    # Text Search 사용 시 관련도 점수 추가
    if use_text_search:
        projection["score"] = {"$meta": "textScore"}

    page_size = 10
    skip = (page - 1) * page_size

    # Count 계산: 근사치 전략 (성능 최적화)
    # Text Search 시 성능을 위해 상위 N개만 검사
    CANDIDATE_LIMIT = 2000
    is_approximate = False
    items = []
    total = 0
    
    if use_text_search:
        # Text Search 최적화: Facet & Barrier 전략
        # 1. $limit으로 후보군 제한
        # 2. $project로 Barrier 생성 (Optimizer Merge 방지)
        # 3. $facet으로 Count와 Data 동시 추출 (Round Trip 감소)
        try:
            pipeline = [
                # 1단계: Text Search & Limit
                {"$match": {"$text": {"$search": q}}},
                {"$limit": CANDIDATE_LIMIT},
                
                # 2단계: Barrier (Optimizer가 $match를 합치지 못하게 함)
                # 필요한 필드만 명시하여 메모리 사용량도 최적화
                {"$project": projection},
            ]
            
            # 3단계: 카테고리 필터링 (Barrier 이후에 실행됨)
            if categories:
                pipeline.append({"$match": {"categories": {"$in": categories}}})
            
            # 4단계: Facet으로 Count와 Data 분리 실행
            pipeline.append({
                "$facet": {
                    "metadata": [{"$count": "total"}],
                    "data": [{"$skip": skip}, {"$limit": page_size}]
                }
            })
            
            result = list(coll.aggregate(pipeline))
            
            # 결과 파싱
            if result:
                facet_result = result[0]
                # Total Count
                metadata = facet_result.get("metadata", [])
                total = metadata[0]["total"] if metadata else 0
                
                # Data Items
                data = facet_result.get("data", [])
                for doc in data:
                    serialize_object_id(doc)
                    doc.pop("score", None)
                    items.append(doc)
            
            # Text Search는 항상 근사치로 간주
            is_approximate = True
            
        except Exception as e:
            logger.error(f"[Search] Facet aggregation failed: {e}")
            raise HTTPException(status_code=500, detail="Search operation failed")
            
    else:
        # 일반 쿼리: 기존 방식 유지 (인덱스 활용)
        total = coll.count_documents(query, limit=10000)
        if total >= 10000:
            is_approximate = True
            
        cursor = coll.find(query, projection).sort([("update_date", -1)]).skip(skip).limit(page_size)
        for doc in cursor:
            serialize_object_id(doc)
            items.append(doc)
    
    total_pages = max(1, math.ceil(total / page_size)) if total else 0

    # 검색 기록 저장 (검색어나 카테고리가 있을 때만)
    if q or categories:
        save_search_history(
            db=db,
            user_id=current_user.id,
            query=q,
            categories=categories,
            result_count=total
        )
        
        # 검색 활동 로그
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
    
    필터 옵션으로 특정 사용자의 검색 기록만 조회 가능합니다.
    최신순으로 정렬되어 반환됩니다.
    
    Args:
        user_id: 특정 사용자의 검색 기록만 조회
        limit: 조회할 기록 수 (기본 100, 최대 1000)
        db: MongoDB Database
    
    Returns:
        SearchHistoryResponse: 검색 기록 목록
    """
    collection = db["search_history"]
    
    query = {}
    if user_id is not None:
        query["user_id"] = user_id
    
    total = collection.count_documents(query)
    
    cursor = collection.find(query).sort("searched_at", -1).limit(limit)
    
    items = []
    for doc in cursor:
        serialize_object_id(doc)
        doc["id"] = doc.pop("_id")
        
        # mock 데이터 호환: 필수 필드 없으면 None 처리
        doc.setdefault("user_id", None)
        doc.setdefault("filters", None)
        doc.setdefault("result_count", None)
        
        items.append(SearchHistoryItem(**doc))
    
    return SearchHistoryResponse(total=total, items=items)


@router.get("/{paper_id}", response_model=Paper)
def get_paper(
    paper_id: str,
    db: Database = Depends(get_mongo_db),
    current_user: User = Depends(get_current_user),  # 인증 필수
):
    coll = db[settings.mongo_collection]

    oid = safe_object_id(paper_id, "paper ID")
    doc = coll.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    # 논문 조회 활동 로그
    log_activity(
        db=db,
        user_id=current_user.id,
        activity_type="view",
        paper_id=paper_id
    )

    return serialize_object_id(doc)