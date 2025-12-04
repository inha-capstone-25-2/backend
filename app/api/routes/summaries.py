"""
논문 요약 API 라우터.

Celery를 사용한 비동기 배치 요약 API를 제공합니다.
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from celery.result import AsyncResult
from app.tasks.summary_tasks import generate_batch_summaries_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/summaries", tags=["summaries"])


# --- Request/Response Schemas ---


class BatchSummaryRequest(BaseModel):
    """배치 요약 요청 스키마"""

    paper_ids: List[str]
    force: bool = False  # 이미 요약된 논문도 강제 재생성


class BatchSummaryStartResponse(BaseModel):
    """배치 요약 시작 응답 스키마"""

    job_id: str
    status: str
    total_papers: int
    message: str


class JobStatusResponse(BaseModel):
    """작업 상태 조회 응답 스키마"""

    job_id: str
    status: str  # PENDING, STARTED, PROGRESS, SUCCESS, FAILURE
    current: Optional[int] = None
    total: Optional[int] = None
    progress_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# --- API Endpoints ---


@router.post("/batch", response_model=BatchSummaryStartResponse, status_code=202)
async def create_batch_summaries(request: BatchSummaryRequest):
    """
    배치 논문 요약 생성 (비동기).

    여러 논문 ID를 받아 Celery 태스크를 시작하고 job_id를 반환합니다.

    Args:
        request: 논문 ID 리스트 및 옵션

    Returns:
        작업 ID 및 상태

    Raises:
        HTTPException: 요청 검증 실패 시
    """
    if not request.paper_ids:
        raise HTTPException(status_code=400, detail="paper_ids는 비어있을 수 없습니다")

    logger.info(
        f"[API] Batch summary request: {len(request.paper_ids)} papers, force={request.force}"
    )

    # Celery 태스크 시작
    task = generate_batch_summaries_task.apply_async(
        args=[request.paper_ids, request.force]
    )

    logger.info(f"[API] Celery task started: {task.id}")

    return BatchSummaryStartResponse(
        job_id=task.id,
        status="pending",
        total_papers=len(request.paper_ids),
        message=f"{len(request.paper_ids)}개 논문의 요약 생성 작업이 시작되었습니다",
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    배치 요약 작업 상태 조회.

    Args:
        job_id: Celery 작업 ID

    Returns:
        작업 진행 상태 및 결과

    Raises:
        HTTPException: 작업 ID가 잘못된 경우
    """
    task_result = AsyncResult(job_id)

    if task_result.state == "PENDING":
        return JobStatusResponse(
            job_id=job_id,
            status="pending",
            progress_message="작업이 대기 중입니다",
        )

    elif task_result.state == "STARTED":
        return JobStatusResponse(
            job_id=job_id,
            status="started",
            progress_message="작업이 시작되었습니다",
        )

    elif task_result.state == "PROGRESS":
        info = task_result.info or {}
        return JobStatusResponse(
            job_id=job_id,
            status="progress",
            current=info.get("current"),
            total=info.get("total"),
            progress_message=info.get("status"),
        )

    elif task_result.state == "SUCCESS":
        result = task_result.result or {}
        return JobStatusResponse(
            job_id=job_id,
            status="success",
            result=result,
            progress_message="작업이 완료되었습니다",
        )

    elif task_result.state == "FAILURE":
        error_msg = str(task_result.info) if task_result.info else "Unknown error"
        return JobStatusResponse(
            job_id=job_id,
            status="failure",
            error=error_msg,
            progress_message="작업이 실패했습니다",
        )

    else:
        return JobStatusResponse(
            job_id=job_id,
            status=task_result.state.lower(),
            progress_message=f"상태: {task_result.state}",
        )


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    """
    배치 요약 작업 취소.

    Args:
        job_id: Celery 작업 ID

    Returns:
        취소 결과

    Raises:
        HTTPException: 작업 취소 실패 시
    """
    task_result = AsyncResult(job_id)

    if task_result.state in ["SUCCESS", "FAILURE"]:
        raise HTTPException(
            status_code=400, detail="이미 완료되거나 실패한 작업은 취소할 수 없습니다"
        )

    try:
        task_result.revoke(terminate=True)
        logger.info(f"[API] Celery task cancelled: {job_id}")
        return {"message": "작업이 취소되었습니다", "job_id": job_id}

    except Exception as e:
        logger.error(f"[API] Failed to cancel task {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"작업 취소 실패: {str(e)}")

