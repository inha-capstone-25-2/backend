"""
MongoDB 컬렉션명 상수 정의.

이 파일은 코드 전반에서 사용되는 MongoDB 컬렉션명을 중앙에서 관리합니다.
하드코딩된 문자열 사용을 방지하여 오타를 예방하고 유지보수성을 향상시킵니다.
"""

# MongoDB 컬렉션명
COLLECTION_USER_ACTIVITIES = "user_activities"
COLLECTION_BOOKMARKS = "bookmarks"
COLLECTION_SEARCH_HISTORY = "search_history"
COLLECTION_PAPER_RECOMMENDATIONS = "paper_recommendations"
COLLECTION_RECOMMENDATION_INTERACTIONS = "recommendation_interactions"
COLLECTION_RECOMMENDATION_EVENTS = "recommendation_events"
COLLECTION_ARXIV_FAILURES = "arxiv_failures"

# 검색 관련 상수
SEARCH_CANDIDATE_LIMIT = 2000  # Text Search 후보 제한
DEFAULT_PAGE_SIZE = 10  # 기본 페이지 크기

# 추천 시스템 관련 상수
RECOMMENDATION_CANDIDATE_LIMIT = 50  # 추천 후보 논문 개수
RECOMMENDATION_TOP_K_DEFAULT = 10  # 기본 추천 개수

# 캐시 관련 상수
USER_CACHE_TTL_SECONDS = 5 * 60  # 사용자 정보 캐시 TTL (5분)
USER_CACHE_MAX_SIZE = 1024  # 사용자 정보 캐시 최대 크기

# TTL (Time To Live) 상수 (초 단위)
TTL_SEARCH_HISTORY_SECONDS = 30 * 24 * 60 * 60  # 30일
TTL_USER_ACTIVITIES_SECONDS = 90 * 24 * 60 * 60  # 90일
TTL_RECOMMENDATION_INTERACTIONS_SECONDS = 60 * 24 * 60 * 60  # 60일
TTL_RECOMMENDATION_EVENTS_SECONDS = 90 * 24 * 60 * 60  # 90일
