"""
캐시 유틸리티 테스트.
"""

import pytest
from app.core.cache import (
    create_search_cache_key,
    get_cached_search_result,
    cache_search_result,
    clear_search_cache,
    get_cache_stats,
)


class TestSearchCache:
    def setup_method(self):
        """각 테스트 전에 캐시 초기화"""
        clear_search_cache()

    def test_create_search_cache_key_basic(self):
        """기본 캐시 키 생성 테스트"""
        key1 = create_search_cache_key("machine learning", ["cs.AI"], 1, "relevance")
        key2 = create_search_cache_key("machine learning", ["cs.AI"], 1, "relevance")

        # 동일한 파라미터는 동일한 키 생성
        assert key1 == key2
        assert key1.startswith("search:")

    def test_create_search_cache_key_different_params(self):
        """서로 다른 파라미터는 다른 키 생성"""
        key1 = create_search_cache_key("machine learning", ["cs.AI"], 1, "relevance")
        key2 = create_search_cache_key("deep learning", ["cs.AI"], 1, "relevance")
        key3 = create_search_cache_key("machine learning", ["cs.AI"], 2, "relevance")
        key4 = create_search_cache_key("machine learning", ["cs.AI"], 1, "view_count")

        # 모두 다른 키
        assert key1 != key2
        assert key1 != key3
        assert key1 != key4

    def test_create_search_cache_key_category_order(self):
        """카테고리 순서 무관하게 동일한 키 생성"""
        key1 = create_search_cache_key("test", ["cs.AI", "cs.LG"], 1, "relevance")
        key2 = create_search_cache_key("test", ["cs.LG", "cs.AI"], 1, "relevance")

        # 카테고리 순서가 달라도 동일한 키
        assert key1 == key2

    def test_create_search_cache_key_none_values(self):
        """None 값 처리 테스트"""
        key1 = create_search_cache_key(None, None, 1, "relevance")
        key2 = create_search_cache_key(None, None, 1, "relevance")

        assert key1 == key2
        assert key1.startswith("search:")

    def test_cache_miss(self):
        """캐시 미스 테스트"""
        result = get_cached_search_result("test", ["cs.AI"], 1, "relevance")
        assert result is None

    def test_cache_hit(self):
        """캐시 히트 테스트"""
        # 캐시에 저장
        mock_result = {"total": 10, "items": []}
        cache_search_result("test", ["cs.AI"], 1, "relevance", mock_result)

        # 캐시에서 조회
        result = get_cached_search_result("test", ["cs.AI"], 1, "relevance")
        assert result is not None
        assert result["total"] == 10

    def test_cache_different_params(self):
        """서로 다른 파라미터는 별도 캐싱"""
        mock_result1 = {"total": 10, "items": []}
        mock_result2 = {"total": 20, "items": []}

        cache_search_result("test1", ["cs.AI"], 1, "relevance", mock_result1)
        cache_search_result("test2", ["cs.AI"], 1, "relevance", mock_result2)

        result1 = get_cached_search_result("test1", ["cs.AI"], 1, "relevance")
        result2 = get_cached_search_result("test2", ["cs.AI"], 1, "relevance")

        assert result1["total"] == 10
        assert result2["total"] == 20

    def test_clear_cache(self):
        """캐시 삭제 테스트"""
        # 캐시에 저장
        mock_result = {"total": 10, "items": []}
        cache_search_result("test", ["cs.AI"], 1, "relevance", mock_result)

        # 캐시 삭제
        clear_search_cache()

        # 캐시 미스 확인
        result = get_cached_search_result("test", ["cs.AI"], 1, "relevance")
        assert result is None

    def test_get_cache_stats(self):
        """캐시 통계 조회 테스트"""
        clear_search_cache()
        stats = get_cache_stats()

        assert stats["current_size"] == 0
        assert stats["max_size"] == 200
        assert stats["ttl"] == 300

        # 아이템 추가
        cache_search_result("test", ["cs.AI"], 1, "relevance", {})
        stats = get_cache_stats()
        assert stats["current_size"] == 1
