"""
Celery 설정.

Redis를 브로커 및 백엔드로 사용하여 비동기 작업을 처리합니다.
"""

from celery import Celery
from app.core.settings import settings

# Redis URL 구성 (settings 객체 사용)
redis_url = f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"

# Celery 앱 생성
celery_app = Celery(
    "paper_summary",
    broker=redis_url,
    backend=redis_url,
    include=["app.tasks.summary_tasks"],
)

# Celery 설정
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1시간 타임아웃
    result_expires=3600,  # 결과 1시간 보관
    # 병렬 워커 설정
    worker_concurrency=5,  # 5개의 워커 프로세스
    worker_prefetch_multiplier=1,  # 각 워커가 한 번에 1개의 태스크만 가져옴 (긴 작업에 적합)
)

if __name__ == "__main__":
    celery_app.start()
