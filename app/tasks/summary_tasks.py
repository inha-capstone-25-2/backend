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
    
    논문을 배치 단위로 처리하여 GPU 서버 효율을 최적화합니다.

    Args:
        self: Celery 태스크 인스턴스
        paper_ids: 요약할 논문 ID 리스트 (빈 리스트면 모든 논문)
        force: 이미 요약된 논문도 강제 재생성

    Returns:
        처리 결과 통계
    """
    start_time = time.time()
    
    # 워커 식별자 추출 (예: W1, W2, ...)
    worker_name = self.request.hostname or "unknown"
    worker_id = worker_name.split("-")[-1] if "-" in worker_name else "0"
    W = f"[W{worker_id}]"  # 짧은 워커 프리픽스
    
    is_all_papers = not paper_ids  # 빈 리스트면 모든 논문
    logger.info(
        f"{W} Task {self.request.id} started: "
        f"{'ALL papers' if is_all_papers else f'{len(paper_ids)} papers'}, "
        f"force={force}"
    )

    try:
        # Celery Worker는 별도 프로세스이므로 MongoDB 연결 초기화 필요
        if db_manager.db is None:
            logger.info(f"{W} Initializing MongoDB connection...")
            db_manager.connect(skip_indexes=True)
        
        db = db_manager.get_db()
        collection = db[settings.mongo_collection]

        # MongoDB에서 논문 조회
        logger.info(f"{W} Building query for papers...")
        if is_all_papers:
            query = {}
            if not force:
                query["summary.ko"] = {"$in": [None, ""]}
        else:
            query = {"_id": {"$in": paper_ids}}
            if not force:
                query["summary.ko"] = {"$in": [None, ""]}

        logger.info(f"{W} Query: {query}")
        
        # 한 번에 최대 100개만 처리
        batch_limit = 100
        
        # 최적화: 필요한 필드만 projection으로 가져오기
        projection = {
            "_id": 1,
            "title": 1,
            "summary.en": 1,
            "authors": 1,
        }
        
        # 최적화: count_documents는 느리므로, force=True이고 전체 문서일 때는 estimated_document_count 사용
        if is_all_papers and force:
            # estimated_document_count는 메타데이터 기반으로 매우 빠름
            total_count = collection.estimated_document_count()
            logger.info(f"{W} Estimated total documents: {total_count}")
        elif is_all_papers and not force:
            # 요약이 없는 문서만 카운트 - 인덱스가 있으면 빠름
            # 전체 카운트 대신 바로 find로 진행
            total_count = -1  # 나중에 계산
            logger.info(f"{W} Skipping count for performance, fetching documents directly...")
        else:
            total_count = len(paper_ids)
            logger.info(f"{W} Requested paper count: {total_count}")
        
        # 문서 조회 (projection 적용)
        papers = list(collection.find(query, projection).limit(batch_limit))
        
        if total_count == -1:
            total_count = len(papers)  # 실제 조회된 개수로 대체
            
        total_requested = total_count if is_all_papers else len(paper_ids)

        logger.info(
            f"{W} Found {len(papers)} papers to summarize (total: {total_count}, force={force})"
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
        logger.info(f"{W} GPU Server URL: {summary_client.base_url}")

        success_count = 0
        failed_count = 0
        errors = []
        
        # 배치 크기 설정 (GPU 서버 최적화를 위해 50개씩 처리)
        BATCH_SIZE = 50

        # 논문을 배치 단위로 처리 (PDF 추출 → GPU 요약 → DB 저장)
        for batch_start in range(0, len(papers), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(papers))
            batch_papers = papers[batch_start:batch_end]
            batch_num = batch_start // BATCH_SIZE + 1
            total_batches = (len(papers) + BATCH_SIZE - 1) // BATCH_SIZE
            
            batch_start_time = time.time()
            logger.info(f"{W} [Batch {batch_num}/{total_batches}] Processing {len(batch_papers)} papers...")
            
            # 1. 배치 내 모든 논문의 PDF 텍스트 추출
            batch_texts = []
            batch_ids = []
            
            for paper in batch_papers:
                arxiv_id = paper["_id"]
                
                try:
                    pdf_text = fetch_arxiv_pdf_text_sync(arxiv_id)
                    
                    if not pdf_text:
                        logger.warning(f"{W} Failed to extract PDF for {arxiv_id}, using abstract only")
                        full_text = build_raw_text(paper)
                    else:
                        full_text = build_full_text_with_pdf(paper, pdf_text)

                    if not full_text:
                        logger.warning(f"{W} No text found for paper {arxiv_id}")
                        failed_count += 1
                        errors.append(f"No text for {arxiv_id}")
                        continue
                    
                    batch_texts.append(full_text)
                    batch_ids.append(arxiv_id)
                    
                except Exception as e:
                    failed_count += 1
                    errors.append(f"PDF extraction error for {arxiv_id}: {str(e)}")
                    logger.error(f"{W} PDF extraction error for {arxiv_id}: {e}")
            
            if not batch_texts:
                logger.warning(f"{W} [Batch {batch_num}/{total_batches}] No texts to process, skipping...")
                continue
            
            # 2. GPU 서버에 배치 요약 요청
            logger.info(
                f"{W} [Batch {batch_num}/{total_batches}] Sending {len(batch_texts)} texts to GPU server..."
            )
            
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    results = loop.run_until_complete(
                        summary_client.summarize_batch(batch_texts)
                    )
                finally:
                    loop.close()

                if not results or len(results) != len(batch_ids):
                    logger.error(
                        f"{W} [Batch {batch_num}/{total_batches}] "
                        f"Result count mismatch: expected {len(batch_ids)}, got {len(results) if results else 0}"
                    )
                    failed_count += len(batch_ids)
                    for arxiv_id in batch_ids:
                        errors.append(f"Batch result mismatch for {arxiv_id}")
                    continue

                # 3. MongoDB에 결과 저장
                for arxiv_id, result in zip(batch_ids, results):
                    summary_en = result.get("summary_en", "")
                    summary_ko = result.get("summary_ko", "")

                    update_result = collection.update_one(
                        {"_id": arxiv_id},
                        {"$set": {"summary.en": summary_en, "summary.ko": summary_ko}},
                    )

                    if update_result.modified_count > 0:
                        success_count += 1
                    else:
                        failed_count += 1
                        errors.append(f"Failed to update {arxiv_id}")

                batch_duration = time.time() - batch_start_time
                avg_per_paper = batch_duration / len(batch_ids)
                logger.info(
                    f"{W} [Batch {batch_num}/{total_batches}] ✓ Completed {len(batch_ids)} papers "
                    f"in {batch_duration:.1f}s (avg: {avg_per_paper:.1f}s/paper)"
                )

            except Exception as e:
                failed_count += len(batch_ids)
                error_msg = f"Batch {batch_num} GPU error: {str(e)}"
                logger.error(f"{W} [Batch {batch_num}/{total_batches}] {error_msg}")
                for arxiv_id in batch_ids:
                    errors.append(f"GPU error for {arxiv_id}: {str(e)}")

            # 진행률 업데이트
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": batch_end,
                    "total": len(papers),
                    "status": f"처리 중... (Batch {batch_num}/{total_batches})",
                    "success": success_count,
                    "failed": failed_count,
                    "worker": f"W{worker_id}",
                },
            )

        total_duration = time.time() - start_time

        final_result = {
            "total": total_requested,
            "processed": len(papers),
            "success": success_count,
            "failed": failed_count,
            "errors": errors[:10],  # 최대 10개 에러만 반환
            "duration_seconds": round(total_duration, 2),
            "avg_seconds_per_paper": round(total_duration / len(papers), 2) if papers else 0,
            "worker": f"W{worker_id}",
        }

        logger.info(
            f"{W} Task {self.request.id} completed in {total_duration:.2f}s. "
            f"Result: {final_result}"
        )
        return final_result

    except Exception as e:
        logger.error(f"{W} Task {self.request.id} failed: {e}")
        raise
