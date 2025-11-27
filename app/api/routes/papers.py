from fastapi import APIRouter, Query, Depends
from typing import List
import logging
from pymongo.database import Database

from app.db.mongodb import get_mongo_db
from app.schemas.paper import (
    Paper,
    PaperSearchResponse,
    SearchHistoryResponse,
)
from app.api.deps import get_current_user
from app.models.user import User
from app.services.paper_service import PaperService

router = APIRouter(prefix="/papers", tags=["papers"])
logger = logging.getLogger(__name__)


@router.get("/search", response_model=PaperSearchResponse)
def search_papers(
    q: str | None = Query(None, min_length=1, description="검색어"),
    categories: List[str] | None = Query(
        None, description="카테고리 코드(복수 선택 가능)"
    ),
    page: int = Query(1, ge=1, description="페이지 (1부터)"),
    sort_by: str = Query(
        "relevance",
        description="정렬 기준: relevance(관련도), view_count(조회수), update_date(최신순)",
    ),
    db: Database = Depends(get_mongo_db),
    current_user: User = Depends(get_current_user),
):
    service = PaperService(db)
    return service.search_papers(
        user=current_user, q=q, categories=categories, page=page, sort_by=sort_by
    )


@router.get("/search-history", response_model=SearchHistoryResponse)
def get_search_history(
    user_id: int | None = Query(None, description="사용자 ID로 필터링"),
    limit: int = Query(100, ge=1, le=1000, description="조회할 기록 수"),
    db: Database = Depends(get_mongo_db),
):
    """검색 기록 조회 (인증 불필요)."""
    service = PaperService(db)
    return service.get_search_history(user_id=user_id, limit=limit)


@router.get("/viewed", response_model=PaperSearchResponse)
def get_viewed_papers(
    page: int = Query(1, ge=1, description="페이지 (1부터)"),
    limit: int = Query(10, ge=1, le=100, description="페이지당 항목 수"),
    db: Database = Depends(get_mongo_db),
    current_user: User = Depends(get_current_user),
):
    """현재 로그인한 사용자가 조회한 논문 목록을 반환."""
    service = PaperService(db)
    return service.get_viewed_papers(user=current_user, page=page, limit=limit)


@router.get("/{paper_id}", response_model=Paper)
def get_paper(
    paper_id: str,
    db: Database = Depends(get_mongo_db),
    current_user: User = Depends(get_current_user),
):
    """논문 상세 정보 조회."""
    service = PaperService(db)

    # Service raises ResourceNotFoundException if not found
    return service.get_paper_detail(user=current_user, paper_id=paper_id)
