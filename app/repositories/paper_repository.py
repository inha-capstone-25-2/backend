import logging
import math
from datetime import datetime
from typing import List, Dict, Any, Optional

from pymongo.database import Database
from pymongo.collection import Collection
from fastapi import HTTPException

from app.core.settings import settings
from app.core.constants import (
    COLLECTION_SEARCH_HISTORY,
    COLLECTION_USER_ACTIVITIES,
    SEARCH_CANDIDATE_LIMIT,
)
from app.utils.mongodb import serialize_object_id, transform_id_field
from app.schemas.paper import SearchHistoryItem

logger = logging.getLogger(__name__)


class PaperRepository:
    def __init__(self, db: Database):
        self.db = db
        self.papers_collection: Collection = db[settings.mongo_collection]
        self.history_collection: Collection = db[COLLECTION_SEARCH_HISTORY]
        self.activities_collection: Collection = db[COLLECTION_USER_ACTIVITIES]

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
        """논문 검색 로직 (Text Search + Two-Step 전략 포함)"""

        query = {}
        use_text_search = False

        if q:
            query["$text"] = {"$search": q}
            use_text_search = True

        if categories:
            query["categories"] = {"$in": categories}

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

        if use_text_search:
            projection["score"] = {"$meta": "textScore"}

        skip = (page - 1) * page_size

        # 결과 초기화
        items = []
        total = 0
        is_approximate = False

        if use_text_search:
            # Text Search 최적화: Two-Step 전략
            try:
                # Step 1: 후보군 조회
                candidates_cursor = self.papers_collection.find(
                    {"$text": {"$search": q}}, {"score": {"$meta": "textScore"}}
                ).limit(SEARCH_CANDIDATE_LIMIT)

                candidates = []
                for doc in candidates_cursor:
                    candidates.append({"_id": doc["_id"], "score": doc.get("score", 0)})

                if not candidates:
                    return self._build_search_response(page, page_size, 0, [], False)

                # Step 2: 필터링 및 데이터 조회
                candidate_ids = [c["_id"] for c in candidates]
                filter_query = {"_id": {"$in": candidate_ids}}
                if categories:
                    filter_query["categories"] = {"$in": categories}

                data_projection = projection.copy()
                if "score" in data_projection:
                    del data_projection["score"]

                docs_cursor = self.papers_collection.find(filter_query, data_projection)
                docs_map = {doc["_id"]: doc for doc in docs_cursor}

                # Step 3: 결과 조합
                final_items = []
                for cand in candidates:
                    if cand["_id"] in docs_map:
                        doc = docs_map[cand["_id"]]
                        doc["score"] = cand["score"]
                        final_items.append(doc)

                # 정렬
                self._sort_items(final_items, sort_by)

                total = len(final_items)
                is_approximate = True

                # Step 4: 페이징
                items = final_items[skip : skip + page_size]

                # 후처리
                for item in items:
                    transform_id_field(item)
                    item.pop("score", None)

            except Exception as e:
                logger.error(f"[Search] Two-step search failed: {e}")
                raise HTTPException(status_code=500, detail="Search operation failed")

        else:
            # 일반 쿼리
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

    def _sort_items(self, items: List[Dict], sort_by: str):
        if sort_by == "view_count":
            items.sort(key=lambda x: x.get("view_count", 0), reverse=True)
        elif sort_by == "update_date":
            items.sort(key=lambda x: x.get("update_date", ""), reverse=True)
        else:  # relevance
            items.sort(key=lambda x: x.get("score", 0), reverse=True)

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
