"""
캐싱 유틸리티.

로컬 메모리 기반 캐시를 제공합니다.
"""

import hashlib
import json
import logging
from typing import Any, List, Optional
from cachetools import TTLCache

logger = logging.getLogger(__name__)


# 검색 결과 캐시 (최대 200개, TTL 5분)
search_cache = TTLCache(maxsize=200, ttl=300)


def create_search_cache_key(
    q: str | None,
    categories: List[str] | None,
    page: int,
    sort_by: str,
) -> str:
    """
    검색 파라미터로부터 캐시 키를 생성합니다.

    Args:
        q: 검색어
        categories: 카테고리 필터
        page: 페이지 번호
        sort_by: 정렬 기준

    Returns:
        str: 캐시 키 (MD5 해시)

    Example:
        >>> create_search_cache_key("machine learning", ["cs.AI"], 1, "relevance")
        'search:a1b2c3d4...'
    """
    # 캐시 키 구성 요소 정규화
    key_data = {
        "q": q or "",
        "categories": sorted(categories) if categories else [],
        "page": page,
        "sort_by": sort_by,
    }

    # JSON 직렬화 후 MD5 해시
    key_string = json.dumps(key_data, sort_keys=True)
    hash_key = hashlib.md5(key_string.encode()).hexdigest()

    return f"search:{hash_key}"


def get_cached_search_result(
    q: str | None,
    categories: List[str] | None,
    page: int,
    sort_by: str,
) -> Optional[Any]:
    """
    캐시에서 검색 결과를 조회합니다.

    Args:
        q: 검색어
        categories: 카테고리 필터
        page: 페이지 번호
        sort_by: 정렬 기준

    Returns:
        Optional[Any]: 캐시된 검색 결과 또는 None
    """
    cache_key = create_search_cache_key(q, categories, page, sort_by)

    if cache_key in search_cache:
        logger.info(f"[CACHE HIT] Search cache hit for key: {cache_key[:16]}...")
        return search_cache[cache_key]

    logger.info(f"[CACHE MISS] Search cache miss for key: {cache_key[:16]}...")
    return None


def cache_search_result(
    q: str | None,
    categories: List[str] | None,
    page: int,
    sort_by: str,
    result: Any,
) -> None:
    """
    검색 결과를 캐시에 저장합니다.

    Args:
        q: 검색어
        categories: 카테고리 필터
        page: 페이지 번호
        sort_by: 정렬 기준
        result: 캐시할 검색 결과
    """
    cache_key = create_search_cache_key(q, categories, page, sort_by)
    search_cache[cache_key] = result
    logger.debug(f"[CACHE SAVE] Cached search result for key: {cache_key[:16]}...")


def clear_search_cache() -> None:
    """
    검색 캐시를 모두 삭제합니다.

    관리자용 기능 또는 테스트용으로 사용됩니다.
    """
    search_cache.clear()
    logger.info("[CACHE CLEAR] Search cache cleared")


def get_cache_stats() -> dict:
    """
    캐시 통계를 반환합니다.

    Returns:
        dict: 캐시 크기 및 최대 크기 정보
    """
    return {
        "current_size": len(search_cache),
        "max_size": search_cache.maxsize,
        "ttl": search_cache.ttl,
    }
