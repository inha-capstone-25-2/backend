"""
Celery 설정.

Redis를 브로커 및 백엔드로 사용하여 비동기 작업을 처리합니다.
"""

from celery import Celery
from app.core.settings import settings

redis_url = f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"

celery_app = Celery(
    "paper_summary",
    broker=redis_url,
    backend=redis_url,
    include=["app.tasks.summary_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    result_expires=3600,
    worker_concurrency=5,
    worker_prefetch_multiplier=1,
)

if __name__ == "__main__":
    celery_app.start()
