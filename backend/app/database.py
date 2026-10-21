"""
MongoDB connection setup (PyMongo).

Only actually connects when USE_MOCK_DATA=false. While USE_MOCK_DATA=true,
get_db() is never called by the routes, so this file can sit here unused
without needing a real MONGO_URI yet.
"""

from pymongo import MongoClient
from pymongo.server_api import ServerApi
from app.config import settings

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(settings.MONGO_URI, server_api=ServerApi("1"), serverSelectionTimeoutMS=5000)
    return _client


def get_db():
    """Returns the studentportal database handle."""
    return get_client()[settings.MONGO_DB_NAME]


def ping() -> bool:
    """Quick connectivity check — call this once at startup or in a health route."""
    try:
        get_client().admin.command("ping")
        return True
    except Exception as e:
        print(f"[database] MongoDB ping failed: {e}")
        return False