"""
Tests for RecommendationService.
"""
import pytest
from unittest.mock import MagicMock, patch
from app.services.recommendation_service import RecommendationService


class TestRecommendationService:
    @patch('app.services.recommendation_service.RuleBasedRecommender')
    @patch('app.services.recommendation_service.RecommendationRepository')
    def test_get_recommendations(self, mock_repo_class, mock_recommender_class, mock_mongo_db, mock_postgres_session, sample_user, sample_paper_doc):
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
                    "personalization_score": 0.85
                },
                "reasons": ["High interest match"],
                "paper": sample_paper_doc.copy()
            }
        ]
        mock_recommender_class.return_value = mock_recommender
        
        # Setup mock repository
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        
        service = RecommendationService(mock_mongo_db)
        service.repo = mock_repo
        
        result = service.get_recommendations(
            user=sample_user,
            db_postgres=mock_postgres_session,
            top_k=10
        )
        
        # Verify recommender was called
        assert mock_recommender.recommend.called
        
        # Verify repository logged the recommendations
        assert mock_repo.log_recommendation.called
        
        # Verify result structure
        assert result["user_id"] == sample_user.id
        assert result["recommendation_type"] == "rule_based"
        assert result["total_count"] == 1
        assert len(result["recommendations"]) == 1
        assert result["recommendations"][0].paper_id == "2301.00001"

    @patch('app.services.recommendation_service.RuleBasedRecommender')
    @patch('app.services.recommendation_service.RecommendationRepository')
    def test_get_recommendations_with_custom_limit(self, mock_repo_class, mock_recommender_class, mock_mongo_db, mock_postgres_session, sample_user):
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
            candidate_limit=50
        )
        
        # Verify custom parameters were passed
        call_args = mock_recommender.recommend.call_args
        assert call_args.kwargs["top_k"] == 5
        assert call_args.kwargs["candidate_limit"] == 50

    @patch('app.services.recommendation_service.RuleBasedRecommender')
    @patch('app.services.recommendation_service.RecommendationRepository')
    def test_get_recommendations_empty(self, mock_repo_class, mock_recommender_class, mock_mongo_db, mock_postgres_session, sample_user):
        """Test getting recommendations when none are available."""
        mock_recommender = MagicMock()
        mock_recommender.recommend.return_value = []
        mock_recommender_class.return_value = mock_recommender
        
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        
        service = RecommendationService(mock_mongo_db)
        service.repo = mock_repo
        
        result = service.get_recommendations(
            user=sample_user,
            db_postgres=mock_postgres_session,
            top_k=10
        )
        
        assert result["total_count"] == 0
        assert len(result["recommendations"]) == 0
