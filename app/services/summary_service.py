"""
논문 요약 서비스.

GPU 서버를 사용하여 논문의 배치 요약을 생성하고 MongoDB에 저장합니다.
"""

import logging
from typing import List, Dict, Any
from app.db.mongodb import db_manager
from app.core.settings import settings
from app.clients.summary_client import get_summary_client
from app.pipeline.text_utils import clean_summary_en, build_raw_text
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)


class SummaryService:
    """
    논문 요약 생성 서비스.

    GPU 서버와 통신하여 배치 요약을 생성하고 결과를 MongoDB에 저장합니다.
    """

    def __init__(self):
        self.summary_client = get_summary_client()

    async def generate_summaries_batch(
        self, paper_ids: List[str], force: bool = False
    ) -> Dict[str, Any]:
        """
        배치 논문 요약 생성.

        Args:
            paper_ids: 요약할 논문 ID 리스트
            force: 이미 요약된 논문도 강제 재생성

        Returns:
            처리 결과 통계
        """
        if not paper_ids:
            return {
                "total": 0,
                "skipped": 0,
                "success": 0,
                "failed": 0,
                "errors": [],
            }

        # db_manager.get_db() 직접 사용 (generator 아님)
        db = db_manager.get_db()
        collection = db[settings.mongo_collection]

        # MongoDB에서 논문 조회
        query = {"_id": {"$in": paper_ids}}
        if not force:
            # 이미 요약된 논문 제외
            query["summary.ko"] = {"$in": [None, ""]}

        papers = list(collection.find(query))
        logger.info(
            f"[SummaryService] Found {len(papers)} papers to summarize (force={force})"
        )

        if not papers:
            return {
                "total": len(paper_ids),
                "skipped": len(paper_ids),
                "success": 0,
                "failed": 0,
                "errors": [],
            }

        # 텍스트 추출 및 정리
        texts_to_summarize = []
        paper_id_map = []  # 인덱스와 paper_id 매핑

        for paper in papers:
            try:
                raw_text = build_raw_text(paper)
                if not raw_text:
                    logger.warning(
                        f"[SummaryService] No text found for paper {paper['_id']}"
                    )
                    continue

                cleaned_text = clean_summary_en(raw_text)
                if not cleaned_text:
                    logger.warning(
                        f"[SummaryService] Empty text after cleaning for paper {paper['_id']}"
                    )
                    continue

                texts_to_summarize.append(cleaned_text)
                paper_id_map.append(paper["_id"])

            except Exception as e:
                logger.error(
                    f"[SummaryService] Error extracting text for paper {paper.get('_id')}: {e}"
                )

        if not texts_to_summarize:
            return {
                "total": len(paper_ids),
                "skipped": len(paper_ids) - len(papers),
                "success": 0,
                "failed": len(papers),
                "errors": ["No valid texts to summarize"],
            }

        # GPU 서버에 배치 요약 요청
        try:
            # GPU 서버 응답: [{"summary_en": ..., "summary_ko": ...}, ...]
            results = await self.summary_client.summarize_batch(texts_to_summarize)
            logger.info(
                f"[SummaryService] Received {len(results)} results from GPU server"
            )
        except Exception as e:
            logger.error(f"[SummaryService] GPU server error: {e}")
            return {
                "total": len(paper_ids),
                "skipped": len(paper_ids) - len(papers),
                "success": 0,
                "failed": len(texts_to_summarize),
                "errors": [str(e)],
            }

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
                    logger.debug(f"[SummaryService] Updated summary for {paper_id}")
                else:
                    failed_count += 1
                    errors.append(f"Failed to update {paper_id}")

            except PyMongoError as e:
                failed_count += 1
                error_msg = f"DB error for {paper_id}: {e}"
                logger.error(f"[SummaryService] {error_msg}")
                errors.append(error_msg)

        final_result = {
            "total": len(paper_ids),
            "skipped": len(paper_ids) - len(papers),
            "success": success_count,
            "failed": failed_count,
            "errors": errors,
        }

        logger.info(f"[SummaryService] Batch summary result: {final_result}")
        return final_result


def get_summary_service() -> SummaryService:
    """
    SummaryService 인스턴스 반환.

    Returns:
        SummaryService 인스턴스
    """
    return SummaryService()
