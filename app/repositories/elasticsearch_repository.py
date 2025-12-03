"""
Elasticsearch 기반 논문 검색 Repository.

Elasticsearch를 사용한 논문 검색 로직을 담당합니다.
"""

import logging
from typing import List, Dict, Any
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import (
    ConnectionError as ESConnectionError,
    NotFoundError,
    RequestError,
)

from app.core.settings import settings
from app.utils.mongodb import transform_id_field

logger = logging.getLogger(__name__)


class ElasticsearchRepository:
    """Elasticsearch 검색 Repository"""

    def __init__(self, es_client: Elasticsearch):
        """
        Args:
            es_client: Elasticsearch 클라이언트 인스턴스
        """
        self.es_client = es_client
        self.index_name = settings.es_index_name

    def search_papers(
        self,
        q: str | None,
        categories: List[str] | None,
        page: int,
        page_size: int,
        sort_by: str,
    ) -> Dict[str, Any]:
        """
        Elasticsearch를 사용한 논문 검색.

        Args:
            q: 검색어
            categories: 카테고리 필터
            page: 페이지 번호 (1부터 시작)
            page_size: 페이지 크기
            sort_by: 정렬 기준 (relevance, view_count, update_date)

        Returns:
            Dict: 검색 결과
            {
                "items": [...],
                "total": 검색된 총 개수,
                "is_approximate": False
            }

        Raises:
            ESConnectionError: Elasticsearch 연결 실패
            RequestError: 잘못된 쿼리 요청
        """
        try:
            # Query 구성
            query = self._build_query(q, categories)

            # Sort 구성
            sort = self._build_sort(sort_by)

            # Pagination 계산
            from_offset = (page - 1) * page_size

            # Elasticsearch 검색 실행
            response = self.es_client.search(
                index=self.index_name,
                query=query,
                sort=sort,
                from_=from_offset,
                size=page_size,
                _source=[
                    "_id",
                    "id",
                    "title",
                    "authors",
                    "categories",
                    "update_date",
                    "view_count",
                ],
                track_total_hits=True,  # 정확한 total 계산
            )

            # 결과 파싱
            hits = response.get("hits", {})
            total = hits.get("total", {}).get("value", 0)
            items = []

            for hit in hits.get("hits", []):
                doc = hit["_source"]
                # _id를 id로 변환
                doc["id"] = hit["_id"]
                items.append(doc)

            logger.info(
                f"[ES] Search completed: q='{q}', categories={categories}, "
                f"total={total}, returned={len(items)}"
            )

            return {
                "items": items,
                "total": total,
                "is_approximate": False,
            }

        except ESConnectionError as e:
            logger.error(f"[ES] Connection error during search: {e}")
            raise
        except NotFoundError as e:
            logger.error(f"[ES] Index not found: {self.index_name}")
            raise
        except RequestError as e:
            logger.error(f"[ES] Invalid search request: {e}")
            raise
        except Exception as e:
            logger.error(f"[ES] Unexpected error during search: {e}")
            raise

    def _build_query(
        self, q: str | None, categories: List[str] | None
    ) -> Dict[str, Any]:
        """
        Elasticsearch 쿼리 빌더.

        Args:
            q: 검색어
            categories: 카테고리 필터

        Returns:
            Dict: Elasticsearch query DSL
        """
        # 기본 쿼리: match_all
        if not q and not categories:
            return {"match_all": {}}

        # Bool query 구성
        must = []
        filter_clauses = []

        # 텍스트 검색
        if q:
            # Multi-match 쿼리: title, authors 필드 검색
            must.append(
                {
                    "multi_match": {
                        "query": q,
                        "fields": [
                            "title^3",  # title에 가중치 3
                            "authors^2",  # authors에 가중치 2
                            "summary.en",  # 영문 요약
                        ],
                        "type": "best_fields",
                        "operator": "or",
                        "fuzziness": "AUTO",  # 오타 허용
                    }
                }
            )

        # 카테고리 필터
        if categories:
            filter_clauses.append({"terms": {"categories": categories}})

        # Bool query 조합
        if must or filter_clauses:
            return {
                "bool": {
                    "must": must if must else [],
                    "filter": filter_clauses if filter_clauses else [],
                }
            }

        return {"match_all": {}}

    def _build_sort(self, sort_by: str) -> List[Dict[str, Any]]:
        """
        정렬 조건 빌더.

        Args:
            sort_by: 정렬 기준 (relevance, view_count, update_date)

        Returns:
            List: Elasticsearch sort 배열
        """
        if sort_by == "view_count":
            return [
                {"view_count": {"order": "desc"}},
                {"update_date": {"order": "desc"}},
            ]
        elif sort_by == "update_date":
            return [{"update_date": {"order": "desc"}}]
        else:
            # relevance (default): _score로 정렬
            return [
                {"_score": {"order": "desc"}},
                {"update_date": {"order": "desc"}},
            ]

    def check_index_exists(self) -> bool:
        """
        인덱스 존재 여부 확인.

        Returns:
            bool: 인덱스 존재 여부
        """
        try:
            return self.es_client.indices.exists(index=self.index_name)
        except Exception as e:
            logger.error(f"[ES] Failed to check index existence: {e}")
            return False

    def get_index_mapping(self) -> Dict[str, Any]:
        """
        현재 인덱스의 매핑 정보 조회.

        Returns:
            Dict: 인덱스 매핑 정보
        """
        try:
            mapping = self.es_client.indices.get_mapping(index=self.index_name)
            return mapping
        except Exception as e:
            logger.error(f"[ES] Failed to get index mapping: {e}")
            return {}

    def create_index_if_not_exists(self) -> bool:
        """
        인덱스가 없으면 생성합니다.

        Returns:
            bool: 인덱스 생성 또는 이미 존재 여부
        """
        try:
            if self.check_index_exists():
                logger.info(f"[ES] Index '{self.index_name}' already exists")
                return True

            # 인덱스 매핑 정의
            mapping = {
                "properties": {
                    "id": {"type": "keyword"},  # arXiv ID
                    "title": {"type": "text", "analyzer": "english"},
                    "authors": {"type": "text", "analyzer": "standard"},
                    "summary": {
                        "properties": {
                            "en": {"type": "text", "analyzer": "english"},
                            "ko": {"type": "text", "analyzer": "standard"},
                        }
                    },
                    "categories": {"type": "keyword"},
                    "update_date": {"type": "date"},
                    "view_count": {"type": "integer"},
                    "bookmark_count": {"type": "integer"},
                }
            }

            # 인덱스 생성
            self.es_client.indices.create(
                index=self.index_name,
                mappings=mapping,
                settings={"number_of_shards": 1, "number_of_replicas": 0},
            )

            logger.info(f"[ES] Successfully created index '{self.index_name}'")
            return True

        except Exception as e:
            logger.error(f"[ES] Failed to create index: {e}")
            return False

    def update_mapping(self) -> bool:
        """
        인덱스 매핑을 업데이트합니다 (새로운 필드 추가 등).
        """
        try:
            if not self.check_index_exists():
                return self.create_index_if_not_exists()

            # 추가할 필드 정의
            mapping = {
                "properties": {
                    "view_count": {"type": "long"},
                    "bookmark_count": {"type": "long"},
                }
            }

            self.es_client.indices.put_mapping(index=self.index_name, body=mapping)
            logger.info(f"[ES] Successfully updated mapping for '{self.index_name}'")
            return True

        except Exception as e:
            logger.error(f"[ES] Failed to update mapping: {e}")
            return False
