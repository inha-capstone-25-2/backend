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

router = APIRouter(prefix="/summaries", tags=["summaries"])


class BatchSummaryRequest(BaseModel):
    """배치 요약 요청 스키마"""

    paper_ids: Optional[List[str]] = None  # None이면 모든 논문 처리
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


@router.post("/batch", response_model=BatchSummaryStartResponse, status_code=202)
async def create_batch_summaries(request: BatchSummaryRequest):
    """
    배치 논문 요약 생성 (비동기).

    여러 논문 ID를 받아 Celery 태스크를 시작하고 job_id를 반환합니다.
    paper_ids가 없으면 모든 논문을 처리합니다.
    Celery 설정의 worker_concurrency만큼 여러 워커가 병렬로 처리합니다.

    Args:
        request: 논문 ID 리스트 및 옵션 (paper_ids가 None이면 모든 논문)

    Returns:
        작업 ID 및 상태

    Raises:
        HTTPException: 요청 검증 실패 시
    """
    from app.celery import celery_app
    from celery import group
    
    paper_ids = request.paper_ids if request.paper_ids else []
    
    # Celery 워커 수 가져오기
    num_chunks = celery_app.conf.get('worker_concurrency', 1) or 1

    logger.info(
        f"[API] Batch summary request: "
        f"{'ALL papers' if not paper_ids else f'{len(paper_ids)} papers'}, "
        f"force={request.force}, workers={num_chunks}"
    )

    # 모든 논문을 처리하는 경우, 여러 태스크로 분할하여 병렬 실행
    if num_chunks > 1 and not paper_ids:
        # 각 청크별 태스크 생성
        tasks = []
        for i in range(num_chunks):
            task = generate_batch_summaries_task.s(
                paper_ids,
                request.force,
                i,
                num_chunks
            )
            tasks.append(task)
        
        # Celery Group으로 병렬 실행
        job = group(tasks).apply_async()
        job_id = job.id
        
        logger.info(f"[API] Celery group started with {num_chunks} tasks: {job_id}")
        
        return BatchSummaryStartResponse(
            job_id=job_id,
            status="pending",
            total_papers=0,
            message=f"모든 논문의 요약 생성 작업이 {num_chunks}개 워커로 시작되었습니다",
        )
    else:
        # 단일 태스크 실행
        task = generate_batch_summaries_task.apply_async(
            args=[paper_ids, request.force, 0, 1]
        )
        
        logger.info(f"[API] Celery task started: {task.id}")
        
        total_msg = "모든 논문" if not paper_ids else f"{len(paper_ids)}개 논문"
        
        return BatchSummaryStartResponse(
            job_id=task.id,
            status="pending",
            total_papers=len(paper_ids) if paper_ids else 0,
            message=f"{total_msg}의 요약 생성 작업이 시작되었습니다",
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

