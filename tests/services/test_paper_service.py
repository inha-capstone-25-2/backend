"""
Tests for PaperService.
"""
import pytest
from unittest.mock import MagicMock, patch
from app.services.paper_service import PaperService


class TestPaperService:
    @patch('app.services.paper_service.PaperRepository')
    @patch('app.services.paper_service.log_activity')
    def test_search_papers_with_logging(self, mock_log_activity, mock_repo_class, mock_mongo_db, sample_user):
        """Test search papers with history and activity logging."""
        # Setup mock repository
        mock_repo = MagicMock()
        mock_repo.search_papers.return_value = {
            "page": 1,
            "page_size": 10,
            "total": 5,
            "items": []
        }
        mock_repo_class.return_value = mock_repo
        
        # Create service
        service = PaperService(mock_mongo_db)
        service.repo = mock_repo
        
        # Execute search with query
        result = service.search_papers(
            user=sample_user,
            q="machine learning",
            categories=None,
            page=1,
            sort_by="relevance"
        )
        
        # Verify search was called
        assert mock_repo.search_papers.called
        
        # Verify history was saved
        assert mock_repo.save_search_history.called
        
        # Verify activity was logged
        assert mock_log_activity.called

    @patch('app.services.paper_service.PaperRepository')
    def test_get_paper_detail(self, mock_repo_class, mock_mongo_db, sample_user, sample_paper_doc):
        """Test getting paper detail."""
        mock_repo = MagicMock()
        mock_repo.get_paper_and_increment_view.return_value = sample_paper_doc
        mock_repo_class.return_value = mock_repo
        
        service = PaperService(mock_mongo_db)
        service.repo = mock_repo
        
        result = service.get_paper_detail(user=sample_user, paper_id="2301.00001")
        
        assert result is not None
        assert mock_repo.get_paper_and_increment_view.called
