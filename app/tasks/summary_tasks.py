"""
요약 생성 Celery 태스크.

배치 요약 생성을 비동기로 처리합니다.
배치 실패 시 작은 배치로 분할하여 재시도합니다.
"""

import logging
import time
import asyncio
from typing import List, Dict, Any, Tuple
from app.celery import celery_app
from app.db.mongodb import db_manager
from app.core.settings import settings
from app.pipeline.text_utils import build_raw_text, build_full_text_with_pdf
from app.pipeline.pdf_extractor import fetch_arxiv_pdf_text_sync
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)


def _process_batch_with_retry(
    summary_client,
    batch_texts: List[str],
    batch_ids: List[str],
    collection,
    retry_batch_size: int,
    worker_prefix: str,
    batch_info: str,
) -> Tuple[int, int, List[str]]:
    """배치 요약을 처리하고, 실패 시 작은 배치로 분할하여 재시도한다.

    Args:
        summary_client: SummaryClient 인스턴스
        batch_texts: 요약할 텍스트 리스트
        batch_ids: 논문 ID 리스트
        collection: MongoDB 컬렉션
        retry_batch_size: 재시도 시 배치 크기
        worker_prefix: 로깅용 워커 프리픽스
        batch_info: 로깅용 배치 정보

    Returns:
        (성공 개수, 실패 개수, 에러 메시지 리스트) 튜플
    """
    from app.core.exceptions import SummaryServerException, GPUTimeoutException
    
    success_count = 0
    failed_count = 0
    errors = []

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
                f"{worker_prefix} [{batch_info}] "
                f"Result count mismatch: expected {len(batch_ids)}, got {len(results) if results else 0}"
            )
            failed_count += len(batch_ids)
            for arxiv_id in batch_ids:
                errors.append(f"Batch result mismatch for {arxiv_id}")
            return success_count, failed_count, errors

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

        return success_count, failed_count, errors

    except (SummaryServerException, GPUTimeoutException) as e:
        logger.warning(
            f"{worker_prefix} [{batch_info}] Batch failed ({type(e).__name__}), "
            f"retrying with smaller batches of {retry_batch_size}..."
        )
        
        return _retry_with_smaller_batches(
            summary_client=summary_client,
            batch_texts=batch_texts,
            batch_ids=batch_ids,
            collection=collection,
            retry_batch_size=retry_batch_size,
            worker_prefix=worker_prefix,
            batch_info=batch_info,
        )

    except Exception as e:
        logger.error(f"{worker_prefix} [{batch_info}] Unexpected error: {e}")
        failed_count = len(batch_ids)
        for arxiv_id in batch_ids:
            errors.append(f"GPU error for {arxiv_id}: {str(e)}")
        return 0, failed_count, errors


def _retry_with_smaller_batches(
    summary_client,
    batch_texts: List[str],
    batch_ids: List[str],
    collection,
    retry_batch_size: int,
    worker_prefix: str,
    batch_info: str,
) -> Tuple[int, int, List[str]]:
    """작은 배치로 분할하여 재시도한다.

    Args:
        summary_client: SummaryClient 인스턴스
        batch_texts: 요약할 텍스트 리스트
        batch_ids: 논문 ID 리스트
        collection: MongoDB 컬렉션
        retry_batch_size: 재시도 배치 크기
        worker_prefix: 로깅용 워커 프리픽스
        batch_info: 로깅용 배치 정보

    Returns:
        (성공 개수, 실패 개수, 에러 메시지 리스트) 튜플
    """
    success_count = 0
    failed_count = 0
    errors = []
    
    total_mini_batches = (len(batch_ids) + retry_batch_size - 1) // retry_batch_size

    for i in range(0, len(batch_ids), retry_batch_size):
        mini_batch_texts = batch_texts[i:i + retry_batch_size]
        mini_batch_ids = batch_ids[i:i + retry_batch_size]
        mini_batch_num = i // retry_batch_size + 1
        
        logger.info(
            f"{worker_prefix} [{batch_info}] Retry mini-batch {mini_batch_num}/{total_mini_batches} "
            f"({len(mini_batch_ids)} papers)..."
        )

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                results = loop.run_until_complete(
                    summary_client.summarize_batch(mini_batch_texts)
                )
            finally:
                loop.close()

            if not results or len(results) != len(mini_batch_ids):
                logger.error(
                    f"{worker_prefix} [{batch_info}] Mini-batch {mini_batch_num} "
                    f"result mismatch"
                )
                failed_count += len(mini_batch_ids)
                for arxiv_id in mini_batch_ids:
                    errors.append(f"Mini-batch result mismatch for {arxiv_id}")
                continue

            for arxiv_id, result in zip(mini_batch_ids, results):
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

            logger.info(
                f"{worker_prefix} [{batch_info}] Mini-batch {mini_batch_num} ✓ "
                f"completed {len(mini_batch_ids)} papers"
            )
            
            if mini_batch_num < total_mini_batches:
                time.sleep(0.5)

        except Exception as e:
            logger.error(
                f"{worker_prefix} [{batch_info}] Mini-batch {mini_batch_num} failed: {e}"
            )
            failed_count += len(mini_batch_ids)
            for arxiv_id in mini_batch_ids:
                errors.append(f"Mini-batch GPU error for {arxiv_id}: {str(e)}")

    return success_count, failed_count, errors


@celery_app.task(bind=True, name="summary_tasks.generate_batch_summaries")
def generate_batch_summaries_task(
    self, paper_ids: List[str], force: bool = False,
    chunk_index: int = 0, total_chunks: int = 1
) -> Dict[str, Any]:
    """
    배치 논문 요약 생성 Celery 태스크.
    
    논문을 배치 단위로 처리하여 GPU 서버 효율을 최적화합니다.
    chunk_index와 total_chunks를 사용하여 여러 워커가 다른 범위를 처리합니다.

    Args:
        self: Celery 태스크 인스턴스
        paper_ids: 요약할 논문 ID 리스트 (빈 리스트면 모든 논문)
        force: 이미 요약된 논문도 강제 재생성
        chunk_index: 현재 청크 인덱스 (0부터 시작)
        total_chunks: 전체 청크 수

    Returns:
        처리 결과 통계
    """
    start_time = time.time()
    
    worker_name = self.request.hostname or "unknown"
    worker_id = worker_name.split("-")[-1] if "-" in worker_name else "0"
    W = f"[W{worker_id}][C{chunk_index}]"
    
    is_all_papers = not paper_ids
    logger.info(
        f"{W} Task {self.request.id} started: "
        f"{'ALL papers' if is_all_papers else f'{len(paper_ids)} papers'}, "
        f"force={force}"
    )

    try:
        if db_manager.db is None:
            logger.info(f"{W} Initializing MongoDB connection...")
            db_manager.connect(skip_indexes=True)
        
        db = db_manager.get_db()
        collection = db[settings.mongo_collection]

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
        
        batch_limit = 100
        
        projection = {
            "_id": 1,
            "title": 1,
            "summary.en": 1,
            "authors": 1,
        }
        
        if is_all_papers and force:
            total_count = collection.estimated_document_count()
            logger.info(f"{W} Estimated total documents: {total_count}")
        elif is_all_papers and not force:
            total_count = -1
            logger.info(f"{W} Skipping count for performance, fetching documents directly...")
        else:
            total_count = len(paper_ids)
            logger.info(f"{W} Requested paper count: {total_count}")
        
        skip_count = chunk_index * batch_limit
        
        logger.info(f"{W} Chunk {chunk_index}/{total_chunks}: skip={skip_count}, limit={batch_limit}")
        
        papers = list(collection.find(query, projection).skip(skip_count).limit(batch_limit))
        
        if total_count == -1:
            total_count = len(papers)
            
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

        from app.clients.summary_client import SummaryClient
        from app.core.exceptions import SummaryServerException, GPUTimeoutException
        
        summary_client = SummaryClient(timeout=settings.summary_request_timeout)
        logger.info(f"{W} GPU Server URL: {summary_client.base_url}")

        success_count = 0
        failed_count = 0
        errors = []
        
        BATCH_SIZE = settings.summary_batch_size
        BATCH_DELAY = settings.summary_batch_delay
        RETRY_BATCH_SIZE = settings.summary_retry_batch_size

        for batch_start in range(0, len(papers), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(papers))
            batch_papers = papers[batch_start:batch_end]
            batch_num = batch_start // BATCH_SIZE + 1
            total_batches = (len(papers) + BATCH_SIZE - 1) // BATCH_SIZE
            
            batch_start_time = time.time()
            logger.info(f"{W} [Batch {batch_num}/{total_batches}] Processing {len(batch_papers)} papers...")
            
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
            
            logger.info(
                f"{W} [Batch {batch_num}/{total_batches}] Sending {len(batch_texts)} texts to GPU server..."
            )
            
            batch_success, batch_failed, batch_errors = _process_batch_with_retry(
                summary_client=summary_client,
                batch_texts=batch_texts,
                batch_ids=batch_ids,
                collection=collection,
                retry_batch_size=RETRY_BATCH_SIZE,
                worker_prefix=W,
                batch_info=f"Batch {batch_num}/{total_batches}",
            )
            
            success_count += batch_success
            failed_count += batch_failed
            errors.extend(batch_errors)

            batch_duration = time.time() - batch_start_time
            if batch_success > 0:
                avg_per_paper = batch_duration / batch_success
                logger.info(
                    f"{W} [Batch {batch_num}/{total_batches}] ✓ Completed {batch_success} papers "
                    f"in {batch_duration:.1f}s (avg: {avg_per_paper:.1f}s/paper)"
                )
            
            if batch_num < total_batches:
                logger.debug(f"{W} Waiting {BATCH_DELAY}s before next batch...")
                time.sleep(BATCH_DELAY)

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
            "errors": errors[:10],
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
