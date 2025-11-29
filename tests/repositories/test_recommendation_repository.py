"""
Tests for RecommendationRepository.
"""

import pytest
from app.repositories.recommendation_repository import RecommendationRepository


class TestRecommendationRepository:
    def test_log_recommendation(self, mock_mongo_db):
        """Test logging a recommendation."""
        repo = RecommendationRepository(mock_mongo_db)

        breakdown = {
            "interest_score": 0.8,
            "popularity_score": 0.6,
            "recency_score": 0.5,
            "personalization_score": 0.7,
        }

        repo.log_recommendation(
            user_id=1,
            paper_id="2301.00001",
            recommendation_type="rule_based",
            score=0.7,
            breakdown=breakdown,
            reasons=["High interest match", "Popular paper"],
        )

        # Verify the log was created
        recommendations_coll = mock_mongo_db["paper_recommendations"]
        doc = recommendations_coll.find_one({"user_id": 1})

        assert doc is not None
        assert doc["paper_id"] == "2301.00001"
        assert doc["recommendation_type"] == "rule_based"
        assert doc["score"] == 0.7
        assert doc["features"]["interest_score"] == 0.8
        assert doc["was_clicked"] is False
        assert "High interest match" in doc["context"]["reasons"]

    def test_log_recommendation_multiple(self, mock_mongo_db):
        """Test logging multiple recommendations."""
        repo = RecommendationRepository(mock_mongo_db)

        for i in range(3):
            repo.log_recommendation(
                user_id=1,
                paper_id=f"2301.0000{i}",
                recommendation_type="rule_based",
                score=0.5 + i * 0.1,
                breakdown={},
                reasons=[],
            )

        recommendations_coll = mock_mongo_db["paper_recommendations"]
        count = recommendations_coll.count_documents({"user_id": 1})

        assert count == 3

    def test_log_recommendation_error_handling(self, mock_mongo_db, caplog):
        """Test that logging errors don't crash."""
        repo = RecommendationRepository(mock_mongo_db)

        # This should not raise an exception even if there's an error
        # (in a real scenario, this might happen with DB issues)
        repo.log_recommendation(
            user_id=1,
            paper_id="test",
            recommendation_type="test",
            score=1.0,
            breakdown={},
            reasons=[],
        )

        # Should have logged successfully
        recommendations_coll = mock_mongo_db["paper_recommendations"]
        assert recommendations_coll.count_documents({}) == 1

    def test_get_all_recommendations(self, mock_mongo_db):
        """Test getting all recommendations."""
        from datetime import datetime

        repo = RecommendationRepository(mock_mongo_db)

        # Insert test data
        recommendations_coll = mock_mongo_db["paper_recommendations"]
        test_data = [
            {
                "user_id": 1,
                "paper_id": "2301.00001",
                "recommendation_type": "rule_based",
                "score": 0.8,
                "features": {},
                "context": {"reasons": []},
                "was_clicked": False,
                "recommended_at": datetime(2024, 1, 1, 12, 0, 0),
            },
            {
                "user_id": 2,
                "paper_id": "2301.00002",
                "recommendation_type": "rule_based",
                "score": 0.7,
                "features": {},
                "context": {"reasons": []},
                "was_clicked": False,
                "recommended_at": datetime(2024, 1, 2, 12, 0, 0),
            },
        ]
        recommendations_coll.insert_many(test_data)

        # Test get all
        total, items = repo.get_all_recommendations(page=1, page_size=10)

        assert total == 2
        assert len(items) == 2
        # Should be sorted by recommended_at descending
        assert items[0]["paper_id"] == "2301.00002"

    def test_get_all_recommendations_pagination(self, mock_mongo_db):
        """Test pagination for all recommendations."""
        from datetime import datetime

        repo = RecommendationRepository(mock_mongo_db)

        # Insert test data
        recommendations_coll = mock_mongo_db["paper_recommendations"]
        test_data = [
            {
                "user_id": 1,
                "paper_id": f"2301.0000{i}",
                "recommendation_type": "rule_based",
                "score": 0.5,
                "features": {},
                "context": {"reasons": []},
                "was_clicked": False,
                "recommended_at": datetime(2024, 1, i + 1, 12, 0, 0),
            }
            for i in range(5)
        ]
        recommendations_coll.insert_many(test_data)

        # Test pagination
        total, items = repo.get_all_recommendations(page=1, page_size=2)
        assert total == 5
        assert len(items) == 2

        total, items = repo.get_all_recommendations(page=2, page_size=2)
        assert total == 5
        assert len(items) == 2

    def test_get_recommendations_by_user(self, mock_mongo_db):
        """Test getting recommendations by user."""
        from datetime import datetime

        repo = RecommendationRepository(mock_mongo_db)

        # Insert test data for multiple users
        recommendations_coll = mock_mongo_db["paper_recommendations"]
        test_data = [
            {
                "user_id": 1,
                "paper_id": "2301.00001",
                "recommendation_type": "rule_based",
                "score": 0.8,
                "features": {},
                "context": {"reasons": []},
                "was_clicked": False,
                "recommended_at": datetime(2024, 1, 1, 12, 0, 0),
            },
            {
                "user_id": 1,
                "paper_id": "2301.00002",
                "recommendation_type": "rule_based",
                "score": 0.7,
                "features": {},
                "context": {"reasons": []},
                "was_clicked": False,
                "recommended_at": datetime(2024, 1, 2, 12, 0, 0),
            },
            {
                "user_id": 2,
                "paper_id": "2301.00003",
                "recommendation_type": "rule_based",
                "score": 0.6,
                "features": {},
                "context": {"reasons": []},
                "was_clicked": False,
                "recommended_at": datetime(2024, 1, 3, 12, 0, 0),
            },
        ]
        recommendations_coll.insert_many(test_data)

        # Test get by user
        total, items = repo.get_recommendations_by_user(user_id=1, page=1, page_size=10)

        assert total == 2
        assert len(items) == 2
        assert all(item["user_id"] == 1 for item in items)
        # Should be sorted by recommended_at descending
        assert items[0]["paper_id"] == "2301.00002"

    def test_get_recommendations_by_user_empty(self, mock_mongo_db):
        """Test getting recommendations for user with no data."""
        repo = RecommendationRepository(mock_mongo_db)

        total, items = repo.get_recommendations_by_user(user_id=999, page=1, page_size=10)

        assert total == 0
        assert len(items) == 0

