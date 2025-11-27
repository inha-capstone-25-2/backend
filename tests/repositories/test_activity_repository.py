"""
Tests for ActivityRepository.
"""
import pytest
from datetime import datetime
from app.repositories.activity_repository import ActivityRepository


class TestActivityRepository:
    def test_get_activities_all(self, mock_mongo_db):
        """Test getting all activities."""
        repo = ActivityRepository(mock_mongo_db)
        
        # Insert test data
        activities_coll = mock_mongo_db["user_activities"]
        activities_coll.insert_many([
            {
                "user_id": 1,
                "activity_type": "view",
                "doi": "2301.00001",
                "timestamp": datetime.utcnow()
            },
            {
                "user_id": 1,
                "activity_type": "bookmark",
                "doi": "2301.00002",
                "timestamp": datetime.utcnow()
            },
            {
                "user_id": 2,
                "activity_type": "view",
                "doi": "2301.00003",
                "timestamp": datetime.utcnow()
            }
        ])
        
        total, items = repo.get_activities(None, None, None, 10)
        
        assert total == 3
        assert len(items) == 3

    def test_get_activities_by_user(self, mock_mongo_db):
        """Test filtering activities by user."""
        repo = ActivityRepository(mock_mongo_db)
        
        activities_coll = mock_mongo_db["user_activities"]
        activities_coll.insert_many([
            {"user_id": 1, "activity_type": "view", "doi": "2301.00001", "timestamp": datetime.utcnow()},
            {"user_id": 2, "activity_type": "view", "doi": "2301.00002", "timestamp": datetime.utcnow()},
        ])
        
        total, items = repo.get_activities(user_id=1, activity_type=None, doi=None, limit=10)
        
        assert total == 1
        assert items[0]["user_id"] == 1

    def test_get_activities_by_type(self, mock_mongo_db):
        """Test filtering activities by type."""
        repo = ActivityRepository(mock_mongo_db)
        
        activities_coll = mock_mongo_db["user_activities"]
        activities_coll.insert_many([
            {"user_id": 1, "activity_type": "view", "doi": "2301.00001", "timestamp": datetime.utcnow()},
            {"user_id": 1, "activity_type": "bookmark", "doi": "2301.00002", "timestamp": datetime.utcnow()},
        ])
        
        total, items = repo.get_activities(user_id=None, activity_type="view", doi=None, limit=10)
        
        assert total == 1
        assert items[0]["activity_type"] == "view"

    def test_get_activities_with_limit(self, mock_mongo_db):
        """Test limiting number of results."""
        repo = ActivityRepository(mock_mongo_db)
        
        activities_coll = mock_mongo_db["user_activities"]
        for i in range(5):
            activities_coll.insert_one({
                "user_id": 1,
                "activity_type": "view",
                "doi": f"2301.0000{i}",
                "timestamp": datetime.utcnow()
            })
        
        total, items = repo.get_activities(None, None, None, limit=3)
        
        assert total == 5
        assert len(items) == 3

    def test_get_activities_metadata_handling(self, mock_mongo_db):
        """Test that missing metadata is set to None."""
        repo = ActivityRepository(mock_mongo_db)
        
        activities_coll = mock_mongo_db["user_activities"]
        activities_coll.insert_one({
            "user_id": 1,
            "activity_type": "search",
            "doi": None,
            "timestamp": datetime.utcnow()
            # No metadata field
        })
        
        total, items = repo.get_activities(None, None, None, 10)
        
        assert items[0]["metadata"] is None
