"""
Tests for ActivityService.
"""
import pytest
from unittest.mock import MagicMock, patch
from app.services.activity_service import ActivityService
from app.schemas.activity import UserActivityOut


class TestActivityService:
    @patch('app.services.activity_service.ActivityRepository')
    def test_get_activities(self, mock_repo_class, mock_mongo_db):
        """Test getting activities."""
        # Setup mock repository
        mock_repo = MagicMock()
        mock_repo.get_activities.return_value = (
            5,  # total
            [
                {"id": "1", "user_id": 1, "activity_type": "view", "doi": "2301.00001", "timestamp": "2023-01-01", "metadata": None},
                {"id": "2", "user_id": 1, "activity_type": "bookmark", "doi": "2301.00002", "timestamp": "2023-01-02", "metadata": None},
            ]
        )
        mock_repo_class.return_value = mock_repo
        
        service = ActivityService(mock_mongo_db)
        service.repo = mock_repo
        
        result = service.get_activities(user_id=1, activity_type=None, doi=None, limit=10)
        
        assert result["total"] == 5
        assert len(result["items"]) == 2
        assert mock_repo.get_activities.called

    @patch('app.services.activity_service.ActivityRepository')
    def test_get_activities_with_filters(self, mock_repo_class, mock_mongo_db):
        """Test getting activities with filters."""
        mock_repo = MagicMock()
        mock_repo.get_activities.return_value = (1, [])
        mock_repo_class.return_value = mock_repo
        
        service = ActivityService(mock_mongo_db)
        service.repo = mock_repo
        
        service.get_activities(
            user_id=1,
            activity_type="view",
            doi="2301.00001",
            limit=50
        )
        
        # Verify filters were passed to repository
        mock_repo.get_activities.assert_called_once_with(1, "view", "2301.00001", 50)

    @patch('app.services.activity_service.ActivityRepository')
    def test_get_activities_empty(self, mock_repo_class, mock_mongo_db):
        """Test getting activities when none exist."""
        mock_repo = MagicMock()
        mock_repo.get_activities.return_value = (0, [])
        mock_repo_class.return_value = mock_repo
        
        service = ActivityService(mock_mongo_db)
        service.repo = mock_repo
        
        result = service.get_activities(None, None, None, 10)
        
        assert result["total"] == 0
        assert len(result["items"]) == 0
