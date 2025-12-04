"""
요약 생성 Celery 태스크.

배치 요약 생성을 비동기로 처리합니다.
"""

import logging
import time
import asyncio
from typing import List, Dict, Any
from app.celery import celery_app
from app.db.mongodb import db_manager
from app.core.settings import settings
from app.pipeline.text_utils import build_raw_text, build_full_text_with_pdf
from app.pipeline.pdf_extractor import fetch_arxiv_pdf_text_sync
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="summary_tasks.generate_batch_summaries")
def generate_batch_summaries_task(
    self, paper_ids: List[str], force: bool = False
) -> Dict[str, Any]:
    """
    배치 논문 요약 생성 Celery 태스크.
    
    논문을 1개씩 처리하여 GPU 서버 타임아웃을 방지합니다.

    Args:
        self: Celery 태스크 인스턴스
        paper_ids: 요약할 논문 ID 리스트 (빈 리스트면 모든 논문)
        force: 이미 요약된 논문도 강제 재생성

    Returns:
        처리 결과 통계
    """
    start_time = time.time()
    
    is_all_papers = not paper_ids  # 빈 리스트면 모든 논문
    logger.info(
        f"[Celery] Task {self.request.id} started: "
        f"{'ALL papers' if is_all_papers else f'{len(paper_ids)} papers'}, "
        f"force={force}"
    )

    try:
        # Celery Worker는 별도 프로세스이므로 MongoDB 연결 초기화 필요
        if db_manager.db is None:
            logger.info("[Celery] Initializing MongoDB connection...")
            db_manager.connect(skip_indexes=True)
        
        db = db_manager.get_db()
        collection = db[settings.mongo_collection]

        # MongoDB에서 논문 조회
        logger.info("[Celery] Building query for papers...")
        if is_all_papers:
            query = {}
            if not force:
                query["summary.ko"] = {"$in": [None, ""]}
        else:
            query = {"_id": {"$in": paper_ids}}
            if not force:
                query["summary.ko"] = {"$in": [None, ""]}

        logger.info(f"[Celery] Query: {query}")
        total_count = collection.count_documents(query)
        logger.info(f"[Celery] Total matching documents: {total_count}")
        
        # 한 번에 최대 100개만 처리
        batch_limit = 100
        papers = list(collection.find(query).limit(batch_limit))
        total_requested = total_count if is_all_papers else len(paper_ids)

        logger.info(
            f"[Celery] Found {len(papers)} papers to summarize (total: {total_count}, force={force})"
        )

        if not papers:
            return {
                "total": total_requested,
                "skipped": total_requested,
                "success": 0,
                "failed": 0,
                "errors": [],
            }

        # GPU 클라이언트 초기화
        from app.clients.summary_client import SummaryClient
        summary_client = SummaryClient(timeout=600)  # 10분 타임아웃
        logger.info(f"[Celery] GPU Server URL: {summary_client.base_url}")

        success_count = 0
        failed_count = 0
        errors = []

        # 논문을 1개씩 처리 (PDF 추출 → GPU 요약 → DB 저장)
        for i, paper in enumerate(papers):
            paper_start_time = time.time()
            arxiv_id = paper["_id"]
            
            try:
                logger.info(f"[Celery] [{i+1}/{len(papers)}] Processing paper: {arxiv_id}")
                
                # 1. PDF 텍스트 추출
                pdf_text = fetch_arxiv_pdf_text_sync(arxiv_id)
                
                if not pdf_text:
                    logger.warning(f"[Celery] [{i+1}/{len(papers)}] Failed to extract PDF for {arxiv_id}, using abstract only")
                    full_text = build_raw_text(paper)
                else:
                    full_text = build_full_text_with_pdf(paper, pdf_text)

                if not full_text:
                    logger.warning(f"[Celery] [{i+1}/{len(papers)}] No text found for paper {arxiv_id}")
                    failed_count += 1
                    errors.append(f"No text for {arxiv_id}")
                    continue

                # 2. GPU 서버에 요약 요청 (1개씩 전송)
                logger.info(f"[Celery] [{i+1}/{len(papers)}] Sending to GPU server... (text length: {len(full_text)})")
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    results = loop.run_until_complete(
                        summary_client.summarize_batch([full_text])  # 1개만 전송
                    )
                finally:
                    loop.close()

                if not results:
                    logger.error(f"[Celery] [{i+1}/{len(papers)}] Empty result from GPU server for {arxiv_id}")
                    failed_count += 1
                    errors.append(f"Empty GPU result for {arxiv_id}")
                    continue

                result = results[0]
                summary_en = result.get("summary_en", "")
                summary_ko = result.get("summary_ko", "")

                # 3. MongoDB에 저장
                update_result = collection.update_one(
                    {"_id": arxiv_id},
                    {"$set": {"summary.en": summary_en, "summary.ko": summary_ko}},
                )

                paper_duration = time.time() - paper_start_time
                
                if update_result.modified_count > 0:
                    success_count += 1
                    logger.info(
                        f"[Celery] [{i+1}/{len(papers)}] ✓ Completed {arxiv_id} in {paper_duration:.1f}s"
                    )
                else:
                    failed_count += 1
                    errors.append(f"Failed to update {arxiv_id}")
                    logger.warning(f"[Celery] [{i+1}/{len(papers)}] ✗ Failed to update {arxiv_id}")

                # 진행률 업데이트
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "current": i + 1,
                        "total": len(papers),
                        "status": f"처리 중... ({i+1}/{len(papers)}) - {arxiv_id}",
                        "success": success_count,
                        "failed": failed_count,
                    },
                )

            except Exception as e:
                failed_count += 1
                error_msg = f"Error processing {arxiv_id}: {str(e)}"
                logger.error(f"[Celery] [{i+1}/{len(papers)}] {error_msg}")
                errors.append(error_msg)

        total_duration = time.time() - start_time

        final_result = {
            "total": total_requested,
            "processed": len(papers),
            "success": success_count,
            "failed": failed_count,
            "errors": errors[:10],  # 최대 10개 에러만 반환
            "duration_seconds": round(total_duration, 2),
            "avg_seconds_per_paper": round(total_duration / len(papers), 2) if papers else 0,
        }

        logger.info(
            f"[Celery] Task {self.request.id} completed in {total_duration:.2f}s. "
            f"Result: {final_result}"
        )
        return final_result

    except Exception as e:
        logger.error(f"[Celery] Task {self.request.id} failed: {e}")
        raise
