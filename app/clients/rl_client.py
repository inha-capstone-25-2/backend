"""
RL 추천 서버 HTTP 클라이언트.

GPU 서버의 RL 추천 API와 통신합니다.
- Rule-based 추천
- RL 기반 추천
- 유사 논문 추천
"""

import logging
from typing import List, Dict, Any, Optional
import httpx
from app.core.settings import settings

logger = logging.getLogger(__name__)


def transform_breakdown(raw: Dict[str, float]) -> Dict[str, float]:
    """
    GPU 서버의 breakdown 응답을 백엔드 스키마에 맞게 변환.

    GPU 서버 형식:
        {"keyword": 0.0, "category": 0.0, "popularity": 0.76, "recency": 0.97}

    백엔드 형식:
        {"interest_score": 0.0, "popularity_score": 0.76, "recency_score": 0.97, "personalization_score": 0.0}
    """
    return {
        "interest_score": raw.get("keyword", 0.0) + raw.get("category", 0.0),
        "popularity_score": raw.get("popularity", 0.0),
        "recency_score": raw.get("recency", 0.0),
        "personalization_score": 0.0,  # 향후 RL 기반 점수 추가 가능
    }


class RLClient:
    """RL 추천 서버와 통신하는 HTTP 클라이언트.

    GPU 서버의 추천 API를 호출하고 결과를 변환합니다.

    Attributes:
        base_url: GPU 서버 URL.
        timeout: 요청 타임아웃 (초).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 10.0,
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
        logger.info(f"[RLClient] Initialized with base_url: {self.base_url}")

    async def get_recommendations(
        self,
        user_id: int,
        limit: int = 6,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Rule-based 추천을 조회한다.

        Args:
            user_id: 사용자 ID.
            limit: 추천 개수.
            session_id: 세션 ID.

        Returns:
            recommendations 리스트를 포함한 추천 결과.
        """
        params = {"user_id": user_id, "limit": limit}
        if session_id:
            params["session_id"] = session_id

        return await self._request("/recommendations", params)

    async def get_rl_recommendations(
        self,
        user_id: int,
        limit: int = 6,
        candidate_k: int = 100,
        session_id: Optional[str] = None,
        base_paper_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """RL 기반 추천을 조회한다.

        Args:
            user_id: 사용자 ID.
            limit: 추천 개수.
            candidate_k: 후보군 크기.
            session_id: 세션 ID.
            base_paper_id: 현재 보고 있는 논문 ID (유사도 보너스용).

        Returns:
            recommendations 리스트를 포함한 추천 결과.
        """
        params = {"user_id": user_id, "limit": limit, "candidate_k": candidate_k}
        if session_id:
            params["session_id"] = session_id
        if base_paper_id:
            params["base_paper_id"] = base_paper_id

        return await self._request("/recommendations/rl", params)

    async def get_similar_papers(
        self,
        paper_id: str,
        limit: int = 6,
    ) -> Dict[str, Any]:
        """
        유사 논문 추천 조회.

        Args:
            paper_id: 기준 논문 ID (arXiv ID)
            limit: 추천 개수

        Returns:
            유사 논문 결과 (recommendations 리스트 포함)
        """
        params = {"limit": limit}
        return await self._request(f"/recommendations/similar/{paper_id}", params)

    async def _request(
        self,
        endpoint: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        공통 HTTP GET 요청 처리.

        Args:
            endpoint: API 엔드포인트 경로
            params: Query parameters

        Returns:
            JSON 응답 데이터

        Raises:
            httpx.HTTPError: HTTP 요청 실패 시
        """
        url = f"{self.base_url}{endpoint}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                # breakdown 변환
                if "recommendations" in data:
                    for rec in data["recommendations"]:
                        if "breakdown" in rec:
                            rec["breakdown"] = transform_breakdown(rec["breakdown"])

                logger.info(f"[RLClient] {endpoint} returned {len(data.get('recommendations', []))} items")
                return data

        except httpx.TimeoutException as e:
            logger.error(f"[RLClient] Timeout error for {endpoint}: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"[RLClient] HTTP {e.response.status_code} error for {endpoint}: {e}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"[RLClient] HTTP error for {endpoint}: {e}")
            raise
        except Exception as e:
            logger.error(f"[RLClient] Unexpected error for {endpoint}: {e}")
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
                logger.info(f"[RLClient] Health check: {status}")
                return status == "ok"

        except Exception as e:
            logger.error(f"[RLClient] Health check failed: {e}")
            return False

    async def log_interaction(
        self,
        user_id: int,
        paper_id: str,
        action_type: str,
        recommendation_id: str,
        position: Optional[int] = None,
        dwell_time: Optional[float] = None,
    ) -> Dict[str, Any]:
        """GPU 서버에 상호작용 로그를 전송한다.

        Args:
            user_id: 사용자 ID.
            paper_id: 논문 ID.
            action_type: 행동 유형 ("click" | "bookmark").
            recommendation_id: 추천 세션 ID.
            position: 추천 목록 내 위치.
            dwell_time: 체류 시간 (초).

        Returns:
            GPU 서버 응답 (reward 포함).
        """
        url = f"{self.base_url}/recommendations/interactions"
        payload = {
            "user_id": user_id,
            "paper_id": paper_id,
            "action_type": action_type,
            "recommendation_id": recommendation_id,
        }
        if position is not None:
            payload["position"] = position
        if dwell_time is not None:
            payload["dwell_time"] = dwell_time

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                logger.info(
                    "[RLClient] Logged interaction: user=%d, paper=%s, action=%s, reward=%s",
                    user_id, paper_id, action_type, data.get("reward")
                )
                return data

        except httpx.TimeoutException as e:
            logger.warning("[RLClient] Interaction log timeout: %s", e)
            return {"ok": False, "error": "timeout"}
        except httpx.HTTPError as e:
            logger.warning("[RLClient] Interaction log failed: %s", e)
            return {"ok": False, "error": str(e)}
        except Exception as e:
            logger.warning("[RLClient] Interaction log unexpected error: %s", e)
            return {"ok": False, "error": str(e)}


# 싱글톤 인스턴스
_rl_client: Optional[RLClient] = None


def get_rl_client() -> RLClient:
    """
    RLClient 싱글톤 인스턴스 반환.

    Returns:
        RLClient 인스턴스
    """
    global _rl_client
    if _rl_client is None:
        _rl_client = RLClient()
    return _rl_client
