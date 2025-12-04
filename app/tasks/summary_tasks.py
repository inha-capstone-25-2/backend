"""
요약 생성 Celery 태스크.

배치 요약 생성을 비동기로 처리합니다.
"""

import logging
from typing import List, Dict, Any
from app.celery import celery_app
from app.db.mongodb import get_mongo_db
from app.core.settings import settings
from app.clients.summary_client import get_summary_client
from app.pipeline.text_utils import clean_summary_en, build_raw_text
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="summary_tasks.generate_batch_summaries")
def generate_batch_summaries_task(
    self, paper_ids: List[str], force: bool = False
) -> Dict[str, Any]:
    """
    배치 논문 요약 생성 Celery 태스크.

    Args:
        self: Celery 태스크 인스턴스
        paper_ids: 요약할 논문 ID 리스트
        force: 이미 요약된 논문도 강제 재생성

    Returns:
        처리 결과 통계
    """
    logger.info(
        f"[Celery] Task {self.request.id} started: {len(paper_ids)} papers, force={force}"
    )

    try:
        # MongoDB 연결
        db = get_mongo_db()
        collection = db[settings.mongo_collection]

        # MongoDB에서 논문 조회
        query = {"_id": {"$in": paper_ids}}
        if not force:
            # 이미 요약된 논문 제외
            query["summary.ko"] = {"$in": [None, ""]}

        papers = list(collection.find(query))
        logger.info(
            f"[Celery] Found {len(papers)} papers to summarize (force={force})"
        )

        if not papers:
            return {
                "total": len(paper_ids),
                "skipped": len(paper_ids),
                "success": 0,
                "failed": 0,
                "errors": [],
            }

        # 진행률 업데이트
        self.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": len(papers), "status": "텍스트 추출 중..."},
        )

        # 텍스트 추출 및 정리
        texts_to_summarize = []
        paper_id_map = []

        for i, paper in enumerate(papers):
            try:
                raw_text = build_raw_text(paper)
                if not raw_text:
                    logger.warning(
                        f"[Celery] No text found for paper {paper['_id']}"
                    )
                    continue

                cleaned_text = clean_summary_en(raw_text)
                if not cleaned_text:
                    logger.warning(
                        f"[Celery] Empty text after cleaning for paper {paper['_id']}"
                    )
                    continue

                texts_to_summarize.append(cleaned_text)
                paper_id_map.append(paper["_id"])

            except Exception as e:
                logger.error(
                    f"[Celery] Error extracting text for paper {paper.get('_id')}: {e}"
                )

        if not texts_to_summarize:
            return {
                "total": len(paper_ids),
                "skipped": len(paper_ids) - len(papers),
                "success": 0,
                "failed": len(papers),
                "errors": ["No valid texts to summarize"],
            }

        # 진행률 업데이트
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": len(texts_to_summarize),
                "status": "GPU 서버에 요약 요청 중...",
            },
        )

        # GPU 서버에 배치 요약 요청 (동기 처리)
        summary_client = get_summary_client()
        
        # 동기 방식으로 요청하기 위해 asyncio 사용
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # GPU 서버 응답: [{"summary_en": ..., "summary_ko": ...}, ...]
            results = loop.run_until_complete(
                summary_client.summarize_batch(texts_to_summarize)
            )
            logger.info(
                f"[Celery] Received {len(results)} results from GPU server"
            )
        finally:
            loop.close()

        # 진행률 업데이트
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": len(results),
                "status": "MongoDB에 저장 중...",
            },
        )

        # MongoDB에 일괄 업데이트 (summary.en, summary.ko 모두 저장)
        success_count = 0
        failed_count = 0
        errors = []

        for i, result in enumerate(results):
            if i >= len(paper_id_map):
                break

            paper_id = paper_id_map[i]
            summary_en = result.get("summary_en", "")
            summary_ko = result.get("summary_ko", "")

            try:
                update_result = collection.update_one(
                    {"_id": paper_id},
                    {"$set": {"summary.en": summary_en, "summary.ko": summary_ko}},
                )

                if update_result.modified_count > 0:
                    success_count += 1
                    logger.debug(f"[Celery] Updated summary for {paper_id}")
                else:
                    failed_count += 1
                    errors.append(f"Failed to update {paper_id}")

                # 진행률 업데이트 (매 10개마다)
                if (i + 1) % 10 == 0:
                    self.update_state(
                        state="PROGRESS",
                        meta={
                            "current": i + 1,
                            "total": len(results),
                            "status": f"저장 중... ({i+1}/{len(results)})",
                        },
                    )

            except PyMongoError as e:
                failed_count += 1
                error_msg = f"DB error for {paper_id}: {e}"
                logger.error(f"[Celery] {error_msg}")
                errors.append(error_msg)

        final_result = {
            "total": len(paper_ids),
            "skipped": len(paper_ids) - len(papers),
            "success": success_count,
            "failed": failed_count,
            "errors": errors,
        }

        logger.info(f"[Celery] Task {self.request.id} completed: {final_result}")
        return final_result

    except Exception as e:
        logger.error(f"[Celery] Task {self.request.id} failed: {e}")
        raise
