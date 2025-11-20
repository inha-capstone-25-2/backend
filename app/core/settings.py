from __future__ import annotations
from pathlib import Path
import os
from typing import Sequence
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

def _base_dir() -> Path:
    return Path(__file__).resolve().parents[2]

def _env_files() -> Sequence[Path]:
    base = _base_dir()
    app_env = os.getenv("APP_ENV", "local")
    candidates = [
        base / ".env",
        base / f".env.{app_env}",
        base / ".env.local",
        base / f".env.{app_env}.local",
        base / "env" / app_env / ".env",
    ]
    seen = []
    for p in candidates:
        if p.is_file() and p not in seen:
            seen.append(p)
    return seen

class Settings(BaseSettings):
    app_env: str = Field(default="local", validation_alias="APP_ENV")

    # PostgreSQL: POSTGRES_*만 사용
    db_host: str = Field(default="localhost", validation_alias="POSTGRES_HOST")
    db_port: int = Field(default=5432, validation_alias="POSTGRES_PORT")
    db_user: str = Field(default="postgres", validation_alias="POSTGRES_USER")
    db_password: str = Field(default="", validation_alias="POSTGRES_PASSWORD")
    db_name: str = Field(default="app", validation_alias="POSTGRES_DB")

    # Mongo
    mongo_host: str = Field(default="localhost", validation_alias="MONGO_HOST")
    mongo_port: int = Field(default=27017, validation_alias="MONGO_PORT")
    mongo_user: str | None = Field(default=None, validation_alias="MONGO_USER")
    mongo_password: str | None = Field(default=None, validation_alias="MONGO_PASSWORD")
    mongo_auth_source: str = Field(default="admin", validation_alias="MONGO_AUTH_SOURCE")
    mongo_db: str = Field(default="arxiv", validation_alias="MONGO_DB")
    mongo_collection: str = Field(default="arxiv_papers", validation_alias="MONGO_COLLECTION")

    # Production Mongo (for local env data copy)
    prod_mongo_host: str | None = Field(default=None, validation_alias="PROD_MONGO_HOST")
    prod_mongo_port: int = Field(default=27017, validation_alias="PROD_MONGO_PORT")
    prod_mongo_user: str | None = Field(default=None, validation_alias="PROD_MONGO_USER")
    prod_mongo_password: str | None = Field(default=None, validation_alias="PROD_MONGO_PASSWORD")
    prod_mongo_auth_source: str = Field(default="admin", validation_alias="PROD_MONGO_AUTH_SOURCE")
    prod_mongo_db: str = Field(default="arxiv", validation_alias="PROD_MONGO_DB")
    prod_mongo_collection: str = Field(default="arxiv_papers", validation_alias="PROD_MONGO_COLLECTION")

    # Auth/JWT
    secret_key: str = Field(default="change-me-in-prod", validation_alias="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=60, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
        env_ignore_empty=True,
    )

settings = Settings()