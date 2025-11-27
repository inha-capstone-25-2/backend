"""
pytest fixtures and configuration.
"""

import pytest
from mongomock import MongoClient as MockMongoClient
from unittest.mock import MagicMock


@pytest.fixture
def mock_mongo_db():
    """Mock MongoDB database for testing."""
    client = MockMongoClient()
    db = client["test_db"]
    return db


@pytest.fixture
def mock_postgres_session():
    """Mock PostgreSQL session for testing."""
    session = MagicMock()
    return session


@pytest.fixture
def sample_user():
    """Sample user for testing."""
    user = MagicMock()
    user.id = 1
    user.username = "testuser"
    user.email = "test@example.com"
    return user


@pytest.fixture
def sample_paper_doc():
    """Sample paper document."""
    return {
        "_id": "2301.00001",
        "title": "Test Paper",
        "abstract": "This is a test paper abstract.",
        "authors": "John Doe, Jane Smith",
        "categories": ["cs.AI", "cs.LG"],
        "update_date": "2023-01-01",
        "view_count": 10,
        "keywords": ["machine learning", "AI"],
    }


@pytest.fixture
def mock_settings():
    """Mock settings with correct collection name."""
    from unittest.mock import MagicMock

    mock = MagicMock()
    mock.mongo_collection = "papers"
    return mock


@pytest.fixture
def sample_bookmark_doc():
    """Sample bookmark document."""
    return {
        "user_id": 1,
        "doi": "2301.00001",
        "notes": "Interesting paper",
    }
