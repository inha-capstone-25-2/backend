"""
Tests for PaperRepository.
"""

import pytest
from app.repositories.paper_repository import PaperRepository
from app.core.constants import SEARCH_CANDIDATE_LIMIT


class TestPaperRepository:
    def test_save_search_history(self, mock_mongo_db):
        """Test saving search history."""
        repo = PaperRepository(mock_mongo_db)

        repo.save_search_history(
            user_id=1, query="machine learning", categories=["cs.AI"], result_count=10
        )

        # Verify the document was inserted
        history_coll = mock_mongo_db["search_history"]
        doc = history_coll.find_one({"user_id": 1})

        assert doc is not None
        assert doc["query"] == "machine learning"
        assert doc["filters"]["categories"] == ["cs.AI"]
        assert doc["result_count"] == 10

    def test_get_search_history(self, mock_mongo_db):
        """Test retrieving search history."""
        from datetime import datetime

        repo = PaperRepository(mock_mongo_db)

        # Insert test data with all required fields
        history_coll = mock_mongo_db["search_history"]
        history_coll.insert_one(
            {
                "user_id": 1,
                "query": "test",
                "filters": {"categories": []},
                "result_count": 5,
                "searched_at": datetime.utcnow(),
            }
        )

        result = repo.get_search_history(user_id=1, limit=10)

        assert result["total"] == 1
        assert len(result["items"]) == 1
        assert result["items"][0].query == "test"

    def test_get_paper_and_increment_view(self, mock_mongo_db, sample_paper_doc):
        """Test getting paper and incrementing view count."""
        repo = PaperRepository(mock_mongo_db)

        # Insert test paper - use correct collection name from settings
        papers_coll = mock_mongo_db["papers"]
        papers_coll.insert_one(sample_paper_doc.copy())

        result = repo.get_paper_and_increment_view("2301.00001")

        assert result is not None
        assert result["id"] == "2301.00001"
        assert result["view_count"] == 11  # Incremented from 10
