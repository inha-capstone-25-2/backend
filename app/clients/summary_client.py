"""
GPU 요약 서버 HTTP 클라이언트.

별도의 GPU 서버로 요약 요청을 전송하고 결과를 수신합니다.
"""

import logging
from typing import List, Optional
import httpx
from app.core.settings import settings

logger = logging.getLogger(__name__)


class SummaryClient:
    """
    GPU 요약 서버와 통신하는 HTTP 클라이언트.

    배치 요약 요청 및 헬스 체크를 수행합니다.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 120,
    ):
        """
        Args:
            base_url: GPU 서버 URL (기본값: 환경변수 SUMMARY_SERVER_URL)
            timeout: 요청 타임아웃 (초)
        """
        self.base_url = base_url or getattr(
            settings, "summary_server_url", "http://localhost:8001"
        )
        self.timeout = timeout
        logger.info(f"[SummaryClient] Initialized with base_url: {self.base_url}")

    async def summarize_batch(self, texts: List[str]) -> List[str]:
        """
        배치 텍스트 요약 생성.

        Args:
            texts: 요약할 텍스트 리스트

        Returns:
            요약 결과 리스트

        Raises:
            httpx.HTTPError: HTTP 요청 실패 시
        """
        if not texts:
            return []

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/summarize/batch",
                    json={"texts": texts},
                )
                response.raise_for_status()
                data = response.json()
                summaries = data.get("summaries", [])

                logger.info(
                    f"[SummaryClient] Successfully summarized {len(summaries)} texts"
                )
                return summaries

        except httpx.TimeoutException as e:
            logger.error(f"[SummaryClient] Timeout error: {e}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"[SummaryClient] HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"[SummaryClient] Unexpected error: {e}")
            raise

    async def health_check(self) -> bool:
        """
        GPU 서버 헬스 체크.

        Returns:
            서버가 정상이면 True, 아니면 False
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


# 싱글톤 인스턴스
_summary_client: Optional[SummaryClient] = None


def get_summary_client() -> SummaryClient:
    """
    SummaryClient 싱글톤 인스턴스 반환.

    Returns:
        SummaryClient 인스턴스
    """
    global _summary_client
    if _summary_client is None:
        _summary_client = SummaryClient()
    return _summary_client
