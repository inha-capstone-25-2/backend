import logging
import math
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

from pymongo.database import Database
from pymongo.collection import Collection
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError as ESConnectionError

from app.core.settings import settings
from app.core.exceptions import DatabaseException
from app.core.constants import (
    COLLECTION_SEARCH_HISTORY,
    COLLECTION_USER_ACTIVITIES,
    SEARCH_CANDIDATE_LIMIT,
)
from app.utils.mongodb import serialize_object_id, transform_id_field
from app.schemas.paper import SearchHistoryItem
from app.repositories.elasticsearch_repository import ElasticsearchRepository

logger = logging.getLogger(__name__)


class PaperRepository:
    def __init__(self, db: Database, es_client: Elasticsearch | None = None):
        self.db = db
        self.papers_collection: Collection = db[settings.mongo_collection]
        self.history_collection: Collection = db[COLLECTION_SEARCH_HISTORY]
        self.activities_collection: Collection = db[COLLECTION_USER_ACTIVITIES]
        
        # Elasticsearch Repository (옵션널)
        self.es_repo: ElasticsearchRepository | None = None
        if es_client is not None:
            self.es_repo = ElasticsearchRepository(es_client)
            logger.info("[PaperRepo] Elasticsearch repository initialized")

    def save_search_history(
        self,
        user_id: int,
        query: str | None,
        categories: List[str] | None,
        result_count: int,
    ) -> None:
        """검색 기록을 MongoDB에 저장."""
        history_doc = {
            "user_id": user_id,
            "query": query or "",
            "filters": {"categories": categories or []},
            "result_count": result_count,
            "searched_at": datetime.utcnow(),
        }

        try:
            self.history_collection.insert_one(history_doc)
            logger.debug(f"Search history saved for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to save search history: {e}")

    def search_papers(
        self,
        q: str | None,
        categories: List[str] | None,
        page: int,
        page_size: int,
        sort_by: str,
    ) -> Dict[str, Any]:
        """
        논문 검색 로직 (Elasticsearch 우선, MongoDB Fallback).
        
        Elasticsearch가 활성화되어 있으면 먼저 시도하고,
        실패하거나 비활성화된 경우 MongoDB Text Search를 사용합니다.
        """
        
        if self.es_repo is not None:
            try:
                logger.info("[PaperRepo] Attempting Elasticsearch search")
                result = self._search_with_elasticsearch(
                    q, categories, page, page_size, sort_by
                )
                logger.info("[PaperRepo] Elasticsearch search successful")
                return result
            except Exception as e:
                logger.warning(
                    f"[PaperRepo] Elasticsearch search failed: {e}. "
                    "Falling back to MongoDB"
                )
                # Fallback to MongoDB (아래에서 처리)
        
        logger.info("[PaperRepo] Using MongoDB Text Search")
        return self._search_with_mongodb(q, categories, page, page_size, sort_by)

    def _search_with_elasticsearch(
        self,
        q: str | None,
        categories: List[str] | None,
        page: int,
        page_size: int,
        sort_by: str,
    ) -> Dict[str, Any]:
        """Elasticsearch를 사용한 검색"""
        if self.es_repo is None:
            raise ValueError("Elasticsearch repository not initialized")
        
        # Elasticsearch 검색 실행
        es_result = self.es_repo.search_papers(
            q=q,
            categories=categories,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
        )
        
        # 결과 변환
        items = es_result["items"]
        total = es_result["total"]
        is_approximate = es_result.get("is_approximate", False)
        
        return self._build_search_response(
            page, page_size, total, items, is_approximate
        )

    def _search_with_mongodb(
        self,
        q: str | None,
        categories: List[str] | None,
        page: int,
        page_size: int,
        sort_by: str,
    ) -> Dict[str, Any]:
        """MongoDB Text Search를 사용한 검색 (기존 로직)"""

        # 공통 변수 초기화
        skip = (page - 1) * page_size
        items = []
        total = 0
        is_approximate = False

        # Projection 설정
        projection = {
            "_id": 1,
            "id": 1,
            "title": 1,
            "authors": 1,
            "categories": 1,
            "update_date": 1,
            "view_count": 1,
        }

        if q:
            try:
                start_time = time.time()

                # Step 1: 후보군 조회 (Text Search Score)
                # 쿼리에 categories를 포함시켜 MongoDB가 검색 범위를 좁히도록 유도
                text_query = {"$text": {"$search": q}}
                if categories:
                    text_query["categories"] = {"$in": categories}

                candidates_cursor = self.papers_collection.find(
                    text_query, {"score": {"$meta": "textScore"}}
                ).limit(SEARCH_CANDIDATE_LIMIT)

                candidates = []
                for doc in candidates_cursor:
                    candidates.append({"_id": doc["_id"], "score": doc.get("score", 0)})
                
                step1_time = time.time() - start_time
                logger.info(f"[PERF] Search Step 1 (Text Search): {step1_time:.4f}s, Candidates: {len(candidates)}")

                if not candidates:
                    return self._build_search_response(page, page_size, 0, [], False)

                # Step 2: 데이터 조회 및 정렬
                step2_start = time.time()
                candidate_ids = [c["_id"] for c in candidates]
                filter_query = {"_id": {"$in": candidate_ids}}

                # MongoDB에서 정렬 (인덱스 활용!)
                sort_field = self._get_sort_field(sort_by)
                docs_cursor = self.papers_collection.find(filter_query, projection).sort(sort_field)
                
                # Step 3: 결과 조합
                final_items = []
                
                for doc in docs_cursor:
                    transform_id_field(doc)
                    final_items.append(doc)
                
                step2_time = time.time() - step2_start
                logger.info(f"[PERF] Search Step 2 & 3 (Filter & Fetch): {step2_time:.4f}s, Final Items: {len(final_items)}")

                total = len(final_items)
                is_approximate = True

                # Step 4: 페이징
                items = final_items[skip : skip + page_size]
                
                total_time = time.time() - start_time
                logger.info(f"[PERF] Total Search Time: {total_time:.4f}s")

            except Exception as e:
                logger.error(f"[Search] Two-step search failed: {e}")
                raise DatabaseException("Search operation failed")

        else:
            # 일반 쿼리 (카테고리만 있거나 전체 조회)
            query = {}
            if categories:
                query["categories"] = {"$in": categories}
            
            total = self.papers_collection.count_documents(query, limit=10000)
            if total >= 10000:
                is_approximate = True

            sort_field = self._get_sort_field(sort_by)

            cursor = (
                self.papers_collection.find(query, projection)
                .sort(sort_field)
                .skip(skip)
                .limit(page_size)
            )
            for doc in cursor:
                transform_id_field(doc)
                items.append(doc)

        return self._build_search_response(
            page, page_size, total, items, is_approximate
        )

    def get_search_history(self, user_id: int | None, limit: int) -> Dict[str, Any]:
        """검색 기록 조회"""
        query = {}
        if user_id is not None:
            query["user_id"] = user_id

        total = self.history_collection.count_documents(query)
        cursor = (
            self.history_collection.find(query).sort("searched_at", -1).limit(limit)
        )

        items = []
        for doc in cursor:
            transform_id_field(doc)
            # Pydantic 모델 호환성을 위한 기본값 처리
            doc.setdefault("user_id", None)
            doc.setdefault("filters", None)
            doc.setdefault("result_count", None)
            items.append(SearchHistoryItem(**doc))

        return {"total": total, "items": items}

    def get_viewed_papers(self, user_id: int, page: int, limit: int) -> Dict[str, Any]:
        """내가 본 논문 조회 (Aggregation)"""
        query = {"user_id": user_id, "activity_type": "view"}

        # Aggregation Pipeline
        pipeline = [
            {"$match": query},
            {"$sort": {"timestamp": -1}},
            {"$group": {"_id": "$doi", "last_viewed": {"$first": "$timestamp"}}},
            {"$sort": {"last_viewed": -1}},
            {"$skip": (page - 1) * limit},
            {"$limit": limit},
        ]

        viewed_papers = list(self.activities_collection.aggregate(pipeline))

        # Count Pipeline
        count_pipeline = [
            {"$match": query},
            {"$group": {"_id": "$doi"}},
            {"$count": "total"},
        ]
        count_result = list(self.activities_collection.aggregate(count_pipeline))
        total = count_result[0]["total"] if count_result else 0

        # 논문 상세 정보 조회
        paper_ids = [item["_id"] for item in viewed_papers if item["_id"]]
        items = []

        if paper_ids:
            paper_docs = self.papers_collection.find(
                {"_id": {"$in": paper_ids}},
                {
                    "_id": 1,
                    "id": 1,
                    "title": 1,
                    "authors": 1,
                    "categories": 1,
                    "update_date": 1,
                    "view_count": 1,
                },
            )
            papers_map = {doc["_id"]: doc for doc in paper_docs}

            for viewed in viewed_papers:
                paper_id = viewed["_id"]
                if paper_id in papers_map:
                    doc = papers_map[paper_id]
                    transform_id_field(doc)
                    items.append(doc)

        return self._build_search_response(page, limit, total, items, False)

    def get_paper_and_increment_view(self, paper_id: str) -> Dict[str, Any] | None:
        """논문 상세 조회 및 조회수 증가"""
        doc = self.papers_collection.find_one_and_update(
            {"_id": paper_id}, {"$inc": {"view_count": 1}}, return_document=True
        )

        if doc:
            transform_id_field(doc)

        return doc

    # --- Helper Methods ---

    def _get_sort_field(self, sort_by: str):
        if sort_by == "view_count":
            return [("view_count", -1), ("update_date", -1)]
        elif sort_by == "update_date":
            return [("update_date", -1)]
        else:
            return [("update_date", -1)]

    def _build_search_response(self, page, page_size, total, items, is_approximate):
        total_pages = max(1, math.ceil(total / page_size)) if total else 0
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
