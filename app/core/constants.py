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
COLLECTION_ARXIV_FAILURES = "arxiv_failures"

# 검색 관련 상수
SEARCH_CANDIDATE_LIMIT = 2000  # Text Search 후보 제한
DEFAULT_PAGE_SIZE = 10  # 기본 페이지 크기

# TTL (Time To Live) 상수 (초 단위)
TTL_SEARCH_HISTORY_SECONDS = 30 * 24 * 60 * 60  # 30일
TTL_USER_ACTIVITIES_SECONDS = 90 * 24 * 60 * 60  # 90일

