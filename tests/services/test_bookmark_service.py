"""
Tests for BookmarkService.
"""
import pytest
from unittest.mock import MagicMock, patch
from bson import ObjectId
from app.services.bookmark_service import BookmarkService


class TestBookmarkService:
    @patch('app.services.bookmark_service.BookmarkRepository')
    @patch('app.services.bookmark_service.log_activity')
    def test_create_bookmark_success(self, mock_log_activity, mock_repo_class, mock_mongo_db, sample_user):
        """Test creating a bookmark successfully."""
        mock_repo = MagicMock()
        mock_repo.paper_exists.return_value = True
        mock_repo.find_by_user_and_doi.return_value = None
        mock_repo.create_bookmark.return_value = {
            "id": "123",
            "user_id": 1,
            "doi": "2301.00001",
            "notes": "Test"
        }
        mock_repo_class.return_value = mock_repo
        
        service = BookmarkService(mock_mongo_db)
        service.repo = mock_repo
        
        result = service.create_bookmark(sample_user, "2301.00001", "Test")
        
        assert result["doi"] == "2301.00001"
        assert mock_log_activity.called

    @patch('app.services.bookmark_service.BookmarkRepository')
    def test_create_bookmark_paper_not_found(self, mock_repo_class, mock_mongo_db, sample_user):
        """Test creating bookmark when paper doesn't exist."""
        from app.core.exceptions import ResourceNotFoundException
        
        mock_repo = MagicMock()
        mock_repo.paper_exists.return_value = False
        mock_repo_class.return_value = mock_repo
        
        service = BookmarkService(mock_mongo_db)
        service.repo = mock_repo
        
        with pytest.raises(ResourceNotFoundException):
            service.create_bookmark(sample_user, "9999.99999", "Test")

    @patch('app.services.bookmark_service.BookmarkRepository')
    def test_create_bookmark_duplicate(self, mock_repo_class, mock_mongo_db, sample_user):
        """Test creating duplicate bookmark."""
        from app.core.exceptions import DuplicateResourceException
        
        mock_repo = MagicMock()
        mock_repo.paper_exists.return_value = True
        mock_repo.find_by_user_and_doi.return_value = {"existing": "bookmark"}
        mock_repo_class.return_value = mock_repo
        
        service = BookmarkService(mock_mongo_db)
        service.repo = mock_repo
        
        with pytest.raises(DuplicateResourceException):
            service.create_bookmark(sample_user, "2301.00001", "Test")

    @patch('app.services.bookmark_service.BookmarkRepository')
    def test_delete_bookmark(self, mock_repo_class, mock_mongo_db, sample_user):
        """Test deleting a bookmark."""
        mock_repo = MagicMock()
        mock_repo.delete_bookmark.return_value = {"doi": "2301.00001"}
        mock_repo_class.return_value = mock_repo
        
        service = BookmarkService(mock_mongo_db)
        service.repo = mock_repo
        
        bookmark_id = ObjectId()
        service.delete_bookmark(sample_user, bookmark_id)
        
        assert mock_repo.delete_bookmark.called

    @patch('app.services.bookmark_service.BookmarkRepository')
    def test_delete_bookmark_not_found(self, mock_repo_class, mock_mongo_db, sample_user):
        """Test deleting non-existent bookmark."""
        from app.core.exceptions import ResourceNotFoundException
        
        mock_repo = MagicMock()
        mock_repo.delete_bookmark.return_value = None
        mock_repo_class.return_value = mock_repo
        
        service = BookmarkService(mock_mongo_db)
        service.repo = mock_repo
        
        with pytest.raises(ResourceNotFoundException):
            service.delete_bookmark(sample_user, ObjectId())
