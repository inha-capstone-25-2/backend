"""
요약 생성 Celery 태스크.

배치 요약 생성을 비동기로 처리합니다.
"""

import logging
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

    Args:
        self: Celery 태스크 인스턴스
        paper_ids: 요약할 논문 ID 리스트 (빈 리스트면 모든 논문)
        force: 이미 요약된 논문도 강제 재생성

    Returns:
        처리 결과 통계
    """
    import time
    start_time = time.time()
    
    is_all_papers = not paper_ids  # 빈 리스트면 모든 논문
    logger.info(
        f"[Celery] Task {self.request.id} started: "
        f"{'ALL papers' if is_all_papers else f'{len(paper_ids)} papers'}, "
        f"force={force}"
    )

    try:
        # Celery Worker는 별도 프로세스이므로 MongoDB 연결 초기화 필요
        # 인덱스 생성은 FastAPI 앱 시작 시에만 수행
        if db_manager.db is None:
            logger.info("[Celery] Initializing MongoDB connection...")
            db_manager.connect(skip_indexes=True)
        
        db = db_manager.get_db()
        collection = db[settings.mongo_collection]

        # MongoDB에서 논문 조회
        logger.info("[Celery] Building query for papers...")
        if is_all_papers:
            # 모든 논문 조회
            query = {}
            if not force:
                # 이미 요약된 논문 제외
                query["summary.ko"] = {"$in": [None, ""]}
        else:
            # 특정 논문만 조회
            query = {"_id": {"$in": paper_ids}}
            if not force:
                # 이미 요약된 논문 제외
                query["summary.ko"] = {"$in": [None, ""]}

        logger.info(f"[Celery] Query: {query}")
        logger.info("[Celery] Counting matching documents...")
        total_count = collection.count_documents(query)
        logger.info(f"[Celery] Total matching documents: {total_count}")
        
        # 한 번에 최대 100개만 처리 (배치 크기 제한)
        batch_limit = 100
        logger.info(f"[Celery] Fetching up to {batch_limit} papers...")
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

        # 1. PDF 텍스트 추출 단계
        extract_start_time = time.time()
        logger.info(f"[Celery] Step 1/3: Extracting text from PDFs for {len(papers)} papers...")
        
        self.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": len(papers), "status": "PDF에서 텍스트 추출 중..."},
        )

        texts_to_summarize = []
        paper_id_map = []

        for i, paper in enumerate(papers):
            try:
                arxiv_id = paper["_id"]
                
                # arXiv PDF에서 본문 추출
                pdf_text = fetch_arxiv_pdf_text_sync(arxiv_id)
                
                if not pdf_text:
                    logger.warning(f"[Celery] Failed to extract PDF for {arxiv_id}")
                    # PDF 실패 시 Abstract만 사용
                    full_text = build_raw_text(paper)
                else:
                    # Abstract + PDF 본문 결합
                    full_text = build_full_text_with_pdf(paper, pdf_text)

                if not full_text:
                    logger.warning(f"[Celery] No text found for paper {arxiv_id}")
                    continue

                # 전처리 없이 원문 그대로 전송 (GPU 서버가 처리)
                texts_to_summarize.append(full_text)
                paper_id_map.append(arxiv_id)

                # 진행률 업데이트 (매 5개마다 또는 마지막)
                if (i + 1) % 5 == 0 or (i + 1) == len(papers):
                    progress_percent = int((i + 1) / len(papers) * 100)
                    logger.info(f"[Celery] Extraction progress: {i + 1}/{len(papers)} ({progress_percent}%)")
                    self.update_state(
                        state="PROGRESS",
                        meta={
                            "current": i + 1,
                            "total": len(papers),
                            "status": f"PDF 추출 중... ({i+1}/{len(papers)})",
                        },
                    )

            except Exception as e:
                logger.error(f"[Celery] Error extracting text for paper {paper.get('_id')}: {e}")

        extract_duration = time.time() - extract_start_time
        logger.info(f"[Celery] Step 1/3 Completed. Duration: {extract_duration:.2f}s. Valid texts: {len(texts_to_summarize)}")

        if not texts_to_summarize:
            return {
                "total": total_requested,
                "skipped": total_requested - len(papers),
                "success": 0,
                "failed": len(papers),
                "errors": ["No valid texts to summarize"],
            }

        # 2. GPU 요약 요청 단계
        gpu_start_time = time.time()
        logger.info(f"[Celery] Step 2/3: Requesting summaries from GPU server for {len(texts_to_summarize)} texts...")

        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": len(texts_to_summarize),
                "status": "GPU 서버에 요약 요청 중...",
            },
        )

        # GPU 서버에 배치 요약 요청 (동기 처리)
        # 매번 새 인스턴스 생성하여 환경변수 변경사항 반영
        from app.clients.summary_client import SummaryClient
        summary_client = SummaryClient()
        logger.info(f"[Celery] GPU Server URL: {summary_client.base_url}")
        
        # 동기 방식으로 요청하기 위해 asyncio 사용
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # GPU 서버 응답: [{"summary_en": ..., "summary_ko": ...}, ...]
            results = loop.run_until_complete(
                summary_client.summarize_batch(texts_to_summarize)
            )
            gpu_duration = time.time() - gpu_start_time
            logger.info(
                f"[Celery] Step 2/3 Completed. Received {len(results)} results. Duration: {gpu_duration:.2f}s"
            )
        finally:
            loop.close()

        # 3. DB 저장 단계
        save_start_time = time.time()
        logger.info(f"[Celery] Step 3/3: Saving summaries to MongoDB...")

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

                # 진행률 업데이트 (매 10개마다 또는 마지막)
                if (i + 1) % 10 == 0 or (i + 1) == len(results):
                    progress_percent = int((i + 1) / len(results) * 100)
                    logger.info(f"[Celery] Saving progress: {i + 1}/{len(results)} ({progress_percent}%)")
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

        save_duration = time.time() - save_start_time
        total_duration = time.time() - start_time

        final_result = {
            "total": total_requested,
            "skipped": total_requested - len(papers),
            "success": success_count,
            "failed": failed_count,
            "errors": errors,
            "duration_seconds": round(total_duration, 2)
        }

        logger.info(
            f"[Celery] Task {self.request.id} completed in {total_duration:.2f}s. "
            f"(Extract: {extract_duration:.2f}s, GPU: {gpu_duration:.2f}s, Save: {save_duration:.2f}s). "
            f"Result: {final_result}"
        )
        return final_result

    except Exception as e:
        logger.error(f"[Celery] Task {self.request.id} failed: {e}")
        raise
