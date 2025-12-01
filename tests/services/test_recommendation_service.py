"""
Tests for RecommendationService.
"""

import pytest
from unittest.mock import MagicMock, patch
from app.services.recommendation_service import RecommendationService


class TestRecommendationService:
    @patch("app.services.recommendation_service.RuleBasedRecommender")
    @patch("app.services.recommendation_service.RecommendationRepository")
    def test_get_recommendations(
        self,
        mock_repo_class,
        mock_recommender_class,
        mock_mongo_db,
        mock_postgres_session,
        sample_user,
        sample_paper_doc,
    ):
        """Test getting recommendations."""
        # Setup mock recommender
        mock_recommender = MagicMock()
        mock_recommender.recommend.return_value = [
            {
                "paper_id": "2301.00001",
                "total_score": 0.85,
                "breakdown": {
                    "interest_score": 0.8,
                    "popularity_score": 0.7,
                    "recency_score": 0.9,
                    "personalization_score": 0.85,
                },
                "reasons": ["High interest match"],
                "paper": sample_paper_doc.copy(),
            }
        ]
        mock_recommender_class.return_value = mock_recommender

        # Setup mock repository
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        service = RecommendationService(mock_mongo_db)
        service.repo = mock_repo

        result = service.get_recommendations(
            user=sample_user, db_postgres=mock_postgres_session, top_k=10
        )

        # Verify recommender was called
        assert mock_recommender.recommend.called

        # Verify repository logged the recommendations (배치로 변경)
        assert mock_repo.log_recommendations_batch.called

        # Verify result structure
        assert result["user_id"] == sample_user.id
        assert result["recommendation_type"] == "rule_based"
        assert result["total_count"] == 1
        assert len(result["recommendations"]) == 1
        assert result["recommendations"][0].paper_id == "2301.00001"

    @patch("app.services.recommendation_service.RuleBasedRecommender")
    @patch("app.services.recommendation_service.RecommendationRepository")
    def test_get_recommendations_with_custom_limit(
        self,
        mock_repo_class,
        mock_recommender_class,
        mock_mongo_db,
        mock_postgres_session,
        sample_user,
    ):
        """Test getting recommendations with custom count."""
        mock_recommender = MagicMock()
        mock_recommender.recommend.return_value = []
        mock_recommender_class.return_value = mock_recommender

        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        service = RecommendationService(mock_mongo_db)
        service.repo = mock_repo

        service.get_recommendations(
            user=sample_user,
            db_postgres=mock_postgres_session,
            top_k=5,
            candidate_limit=50,
        )

        # Verify custom parameters were passed
        # 현재 구현: recommender는 항상 top_k=None으로 호출되어 전체 후보군을 가져온 후
        # 서비스 레이어에서 슬라이싱함
        call_args = mock_recommender.recommend.call_args
        assert call_args.kwargs["top_k"] is None  # 전체 후보군 조회
        assert call_args.kwargs["candidate_limit"] == 50

    @patch("app.services.recommendation_service.RuleBasedRecommender")
    @patch("app.services.recommendation_service.RecommendationRepository")
    def test_get_recommendations_empty(
        self,
        mock_repo_class,
        mock_recommender_class,
        mock_mongo_db,
        mock_postgres_session,
        sample_user,
    ):
        """Test getting recommendations when none are available."""
        mock_recommender = MagicMock()
        mock_recommender.recommend.return_value = []
        mock_recommender_class.return_value = mock_recommender

        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        service = RecommendationService(mock_mongo_db)
        service.repo = mock_repo

        result = service.get_recommendations(
            user=sample_user, db_postgres=mock_postgres_session, top_k=10
        )

        assert result["total_count"] == 0
        assert len(result["recommendations"]) == 0

    @patch("app.services.recommendation_service.RecommendationRepository")
    def test_get_all_recommendation_logs(self, mock_repo_class, mock_mongo_db):
        """Test getting all recommendation logs."""
        from datetime import datetime

        # Setup mock repository
        mock_repo = MagicMock()
        mock_repo.get_all_recommendations.return_value = (
            2,  # total
            [
                {
                    "_id": "507f1f77bcf86cd799439011",
                    "user_id": 1,
                    "paper_id": "2301.00001",
                    "recommendation_type": "rule_based",
                    "score": 0.8,
                    "features": {"interest_score": 0.8},
                    "context": {"reasons": []},
                    "was_clicked": False,
                    "recommended_at": datetime(2024, 1, 1, 12, 0, 0),
                },
                {
                    "_id": "507f1f77bcf86cd799439012",
                    "user_id": 2,
                    "paper_id": "2301.00002",
                    "recommendation_type": "rule_based",
                    "score": 0.7,
                    "features": {"interest_score": 0.7},
                    "context": {"reasons": []},
                    "was_clicked": False,
                    "recommended_at": datetime(2024, 1, 2, 12, 0, 0),
                },
            ],
        )
        mock_repo_class.return_value = mock_repo

        service = RecommendationService(mock_mongo_db)
        service.repo = mock_repo

        result = service.get_all_recommendation_logs(page=1, page_size=20)

        # Verify repository was called
        assert mock_repo.get_all_recommendations.called

        # Verify result structure
        assert result["total"] == 2
        assert result["page"] == 1
        assert result["page_size"] == 20
        assert len(result["items"]) == 2
        assert result["items"][0]["id"] == "507f1f77bcf86cd799439011"
        assert result["items"][0]["user_id"] == 1

    @patch("app.services.recommendation_service.RecommendationRepository")
    def test_get_user_recommendation_logs(self, mock_repo_class, mock_mongo_db):
        """Test getting user recommendation logs."""
        from datetime import datetime

        # Setup mock repository
        mock_repo = MagicMock()
        mock_repo.get_recommendations_by_user.return_value = (
            1,  # total
            [
                {
                    "_id": "507f1f77bcf86cd799439011",
                    "user_id": 1,
                    "paper_id": "2301.00001",
                    "recommendation_type": "rule_based",
                    "score": 0.8,
                    "features": {"interest_score": 0.8},
                    "context": {"reasons": []},
                    "was_clicked": False,
                    "recommended_at": datetime(2024, 1, 1, 12, 0, 0),
                },
            ],
        )
        mock_repo_class.return_value = mock_repo

        service = RecommendationService(mock_mongo_db)
        service.repo = mock_repo

        result = service.get_user_recommendation_logs(user_id=1, page=1, page_size=20)

        # Verify repository was called with correct user_id
        mock_repo.get_recommendations_by_user.assert_called_once_with(1, 1, 20)

        # Verify result structure
        assert result["total"] == 1
        assert result["page"] == 1
        assert result["page_size"] == 20
        assert len(result["items"]) == 1
        assert result["items"][0]["id"] == "507f1f77bcf86cd799439011"
        assert result["items"][0]["user_id"] == 1

