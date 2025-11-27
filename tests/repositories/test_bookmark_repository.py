"""
Tests for BookmarkRepository.
"""
import pytest
from app.repositories.bookmark_repository import BookmarkRepository


class TestBookmarkRepository:
    def test_paper_exists(self, mock_mongo_db, sample_paper_doc):
        """Test checking if paper exists."""
        repo = BookmarkRepository(mock_mongo_db)
        
        # Use correct collection name from settings
        papers_coll = mock_mongo_db["papers"]
        papers_coll.insert_one(sample_paper_doc.copy())
        
        assert repo.paper_exists("2301.00001") is True
        assert repo.paper_exists("9999.99999") is False

    def test_create_bookmark(self, mock_mongo_db):
        """Test creating a bookmark."""
        repo = BookmarkRepository(mock_mongo_db)
        
        result = repo.create_bookmark(
            user_id=1,
            doi="2301.00001",
            notes="Great paper"
        )
        
        assert result is not None
        assert result["user_id"] == 1
        assert result["doi"] == "2301.00001"
        assert result["notes"] == "Great paper"
        assert "id" in result  # _id converted to id

    def test_find_by_user_and_doi(self, mock_mongo_db):
        """Test finding bookmark by user and DOI."""
        repo = BookmarkRepository(mock_mongo_db)
        
        # Create a bookmark
        repo.create_bookmark(user_id=1, doi="2301.00001", notes="Test")
        
        # Find it
        result = repo.find_by_user_and_doi(1, "2301.00001")
        
        assert result is not None
        assert result["doi"] == "2301.00001"

    def test_list_bookmarks(self, mock_mongo_db):
        """Test listing bookmarks."""
        repo = BookmarkRepository(mock_mongo_db)
        
        # Create multiple bookmarks
        repo.create_bookmark(user_id=1, doi="2301.00001", notes="Note 1")
        repo.create_bookmark(user_id=1, doi="2301.00002", notes="Note 2")
        repo.create_bookmark(user_id=2, doi="2301.00003", notes="Note 3")
        
        # List for user 1
        results = repo.list_bookmarks(user_id=1)
        
        assert len(results) == 2
        assert all("id" in r for r in results)
