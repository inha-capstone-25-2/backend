"""
GPU 요약 서버 HTTP 클라이언트.

별도의 GPU 서버로 요약 요청을 전송하고 결과를 수신합니다.
tenacity를 사용한 Exponential backoff 재시도 로직이 포함되어 
504/502/503/429 에러 및 타임아웃을 처리합니다.
"""

import logging
from typing import List, Optional
import httpx
from tenacity import (
    AsyncRetrying,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
    before_sleep_log,
    RetryError,
)
from app.core.settings import settings
from app.core.exceptions import SummaryServerException, GPUTimeoutException

logger = logging.getLogger(__name__)


RETRYABLE_STATUS_CODES = {502, 503, 504, 429}


class SummaryClient:
    """GPU 요약 서버와 통신하는 HTTP 클라이언트.

    배치 요약 요청 및 헬스 체크를 수행합니다.

    Attributes:
        base_url: GPU 서버 URL.
        timeout: 요청 타임아웃 (초).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 300,
    ):
        """인스턴스를 초기화한다.

        Args:
            base_url: GPU 서버 URL. 기본값은 환경변수 GPU_SERVER.
            timeout: 요청 타임아웃 (초).
        """
        self.base_url = base_url or getattr(
            settings, "summary_server_url", "http://localhost:8000"
        )
        self.timeout = timeout
        
        self.max_attempts = getattr(settings, "summary_retry_max_attempts", 5)
        self.initial_delay = getattr(settings, "summary_retry_initial_delay", 2.0)
        self.max_delay = getattr(settings, "summary_retry_max_delay", 60.0)
        
        logger.info(
            f"[SummaryClient] Initialized with base_url: {self.base_url}, "
            f"timeout: {self.timeout}s, max_retries: {self.max_attempts}"
        )

    async def _do_summarize_request(self, texts: List[str]) -> List[dict]:
        """실제 HTTP 요청을 수행한다.

        Args:
            texts: 요약할 텍스트 리스트.

        Returns:
            요약 결과 리스트.

        Raises:
            httpx.TimeoutException: 타임아웃 발생 시.
            SummaryServerException: 재시도 가능한 HTTP 에러 발생 시.
            httpx.HTTPError: 기타 HTTP 에러 발생 시.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/summarize/batch",
                json={"texts": texts},
            )
            
            # 재시도 가능한 상태 코드면 예외 발생
            if response.status_code in RETRYABLE_STATUS_CODES:
                raise SummaryServerException(
                    f"Retryable HTTP error",
                    status_code=response.status_code
                )
            
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])

    async def summarize_batch(self, texts: List[str]) -> List[dict]:
        """배치 텍스트 요약 및 번역을 생성한다 (tenacity exponential backoff 재시도 포함).

        Args:
            texts: 요약할 텍스트 리스트.

        Returns:
            요약 결과 리스트. 각 항목은 summary_en, summary_ko 키를 포함.

        Raises:
            GPUTimeoutException: 모든 재시도 후에도 타임아웃 발생 시.
            SummaryServerException: 모든 재시도 후에도 서버 에러 발생 시.
            httpx.HTTPError: 재시도 불가능한 HTTP 요청 실패 시.
        """
        if not texts:
            return []

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.max_attempts),
                wait=wait_exponential_jitter(
                    initial=self.initial_delay,
                    max=self.max_delay,
                    jitter=self.max_delay * 0.25,
                ),
                retry=retry_if_exception_type((
                    httpx.TimeoutException,
                    SummaryServerException,
                )),
                before_sleep=before_sleep_log(logger, logging.WARNING),
                reraise=True,
            ):
                with attempt:
                    results = await self._do_summarize_request(texts)
                    
                    attempt_num = attempt.retry_state.attempt_number
                    logger.info(
                        f"[SummaryClient] Successfully summarized {len(results)} texts"
                        + (f" (attempt {attempt_num})" if attempt_num > 1 else "")
                    )
                    return results

        except RetryError as e:
            last_exception = e.last_attempt.exception()
            if isinstance(last_exception, httpx.TimeoutException):
                logger.error(
                    f"[SummaryClient] All {self.max_attempts} attempts failed due to timeout"
                )
                raise GPUTimeoutException(
                    f"GPU server timeout after {self.max_attempts} attempts",
                    timeout=self.timeout
                ) from last_exception
            elif isinstance(last_exception, SummaryServerException):
                logger.error(
                    f"[SummaryClient] All {self.max_attempts} attempts failed "
                    f"with status {last_exception.status_code}"
                )
                raise last_exception
            else:
                raise

        except httpx.HTTPError as e:
            logger.error(f"[SummaryClient] Non-retryable HTTP error: {e}")
            raise

        except Exception as e:
            logger.error(f"[SummaryClient] Unexpected error: {e}")
            raise

        return []

    async def health_check(self) -> bool:
        """GPU 서버 헬스 체크를 수행한다.

        Returns:
            서버가 정상이면 True, 아니면 False.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                data = response.json()

                status = data.get("status")
                logger.info(f"[SummaryClient] Health check: {status}")
                return status == "ok"

        except Exception as e:
            logger.error(f"[SummaryClient] Health check failed: {e}")
            return False


_summary_client: Optional[SummaryClient] = None


def get_summary_client() -> SummaryClient:
    """SummaryClient 싱글톤 인스턴스를 반환한다.

    Returns:
        SummaryClient 인스턴스.
    """
    global _summary_client
    if _summary_client is None:
        _summary_client = SummaryClient(
            timeout=settings.summary_request_timeout
        )
    return _summary_client
