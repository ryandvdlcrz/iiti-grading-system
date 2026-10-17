"""
Central place for reading environment variables (.env).
Everything else in the app should import settings from here instead of
calling os.getenv() directly — keeps config in one place.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # reads .env in the project root


class Settings:
    MONGO_URI: str = os.getenv("MONGO_URI", "")
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "studentportal")

    # "true" while we don't have confirmed MongoDB collection names/schema yet.
    # Flip to "false" in .env once studentportal schema is confirmed.
    USE_MOCK_DATA: bool = os.getenv("USE_MOCK_DATA", "true").lower() == "true"

    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

    # Login tokens. SECRET_KEY has no default on purpose: login refuses to
    # work until you set a real one in .env.
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

    # TEMPORARY: while "true", requests with no login token but with the old
    # X-Teacher-Id header are still accepted, so pages not yet switched to the
    # token keep working. Set to "false" in .env once every page sends the token.
    ALLOW_PLACEHOLDER_AUTH: bool = os.getenv("ALLOW_PLACEHOLDER_AUTH", "true").lower() == "true"


settings = Settings()