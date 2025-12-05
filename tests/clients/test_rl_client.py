"""
RL 클라이언트 단위 테스트.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.clients.rl_client import RLClient, transform_breakdown, get_rl_client


class TestTransformBreakdown:
    """breakdown 변환 함수 테스트"""

    def test_transform_breakdown_full(self):
        """모든 필드가 있는 경우"""
        raw = {
            "keyword": 0.5,
            "category": 0.3,
            "popularity": 0.76,
            "recency": 0.97,
        }
        result = transform_breakdown(raw)
        
        assert result["interest_score"] == 0.8  # 0.5 + 0.3
        assert result["popularity_score"] == 0.76
        assert result["recency_score"] == 0.97
        assert result["personalization_score"] == 0.0

    def test_transform_breakdown_partial(self):
        """일부 필드만 있는 경우"""
        raw = {"popularity": 0.5, "recency": 0.8}
        result = transform_breakdown(raw)
        
        assert result["interest_score"] == 0.0
        assert result["popularity_score"] == 0.5
        assert result["recency_score"] == 0.8
        assert result["personalization_score"] == 0.0

    def test_transform_breakdown_empty(self):
        """빈 딕셔너리"""
        result = transform_breakdown({})
        
        assert result["interest_score"] == 0.0
        assert result["popularity_score"] == 0.0
        assert result["recency_score"] == 0.0
        assert result["personalization_score"] == 0.0


class TestRLClient:
    """RLClient 클래스 테스트"""

    @pytest.fixture
    def client(self):
        return RLClient(base_url="http://test-server:8000", timeout=5.0)

    @pytest.mark.asyncio
    async def test_get_rl_recommendations_success(self, client):
        """RL 추천 성공 케이스"""
        mock_response = {
            "user_id": 1,
            "session_id": "test-session",
            "recommendation_type": "rl_based",
            "recommendations": [
                {
                    "paper_id": "2411.02904",
                    "title": "Test Paper",
                    "total_score": 0.85,
                    "breakdown": {
                        "keyword": 0.5,
                        "category": 0.3,
                        "popularity": 0.76,
                        "recency": 0.97,
                    },
                }
            ],
            "total_count": 1,
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response_obj)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.get_rl_recommendations(
                user_id=1, limit=6, session_id="test-session"
            )

            assert result["user_id"] == 1
            assert len(result["recommendations"]) == 1
            # breakdown이 변환되었는지 확인
            breakdown = result["recommendations"][0]["breakdown"]
            assert "interest_score" in breakdown
            assert breakdown["interest_score"] == 0.8

    @pytest.mark.asyncio
    async def test_get_similar_papers_success(self, client):
        """유사 논문 추천 성공 케이스"""
        mock_response = {
            "paper_id": "2411.02904",
            "recommendations": [
                {"paper_id": "2411.02905", "total_score": 0.9, "breakdown": {}},
            ],
            "total_count": 1,
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response_obj)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.get_similar_papers(paper_id="2411.02904", limit=6)

            assert result["paper_id"] == "2411.02904"
            assert len(result["recommendations"]) == 1

    @pytest.mark.asyncio
    async def test_timeout_error(self, client):
        """타임아웃 에러 처리"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(httpx.TimeoutException):
                await client.get_rl_recommendations(user_id=1)

    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """헬스 체크 성공"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = {"status": "ok"}
            mock_response_obj.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response_obj)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        """헬스 체크 실패"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("connection failed"))
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.health_check()
            assert result is False


class TestGetRLClient:
    """싱글톤 함수 테스트"""

    def test_singleton(self):
        """싱글톤 인스턴스 반환 확인"""
        # 모듈 레벨 싱글톤 리셋
        import app.clients.rl_client as module
        module._rl_client = None
        
        client1 = get_rl_client()
        client2 = get_rl_client()
        
        assert client1 is client2
