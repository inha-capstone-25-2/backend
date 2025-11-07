from __future__ import annotations
from pathlib import Path
import os
from typing import Sequence
from pydantic import BaseModel, Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict

def _base_dir() -> Path:
    # 프로젝트 루트 (backend)
    return Path(__file__).resolve().parents[2]

def _env_files() -> Sequence[Path]:
    base = _base_dir()
    app_env = os.getenv("APP_ENV", "local")
    candidates = [
        base / ".env",                          # 기본
        base / f".env.{app_env}",               # 프로필
        base / ".env.local",                    # 로컬 공통 오버라이드
        base / f".env.{app_env}.local",         # 프로필 로컬 오버라이드
        base / "env" / app_env / ".env",        # 서브모듈(backend/env/<APP_ENV>/.env)
    ]
    # 존재하는 파일만 유지(순서대로 로드)
    seen = []
    for p in candidates:
        if p.is_file() and p not in seen:
            seen.append(p)
    return seen

class Settings(BaseSettings):
    # 앱
    app_env: str = Field(default="local", validation_alias="APP_ENV")

    # DB (PostgreSQL 전용)
    db_host: str = Field(
        default="localhost",
        validation_alias=AliasChoices("DB_HOST", "POSTGRES_HOST", "POSTGRESQL_HOST"),
    )
    db_port: int = Field(
        default=5432,
        validation_alias=AliasChoices("DB_PORT", "POSTGRES_PORT", "POSTGRESQL_PORT"),
    )
    db_user: str = Field(
        default="postgres",
        validation_alias=AliasChoices("DB_USER", "POSTGRES_USER", "POSTGRESQL_USER"),
    )
    db_password: str = Field(
        default="",
        validation_alias=AliasChoices("DB_PASSWORD", "POSTGRES_PASSWORD", "POSTGRESQL_PASSWORD"),
    )
    db_name: str = Field(
        default="app",
        validation_alias=AliasChoices("DB_NAME", "POSTGRES_DB", "POSTGRESQL_DB"),
    )

    # Mongo
    mongo_host: str = Field(default="localhost", validation_alias="MONGO_HOST")
    mongo_port: int = Field(default=27017, validation_alias="MONGO_PORT")
    mongo_user: str | None = Field(default=None, validation_alias="MONGO_USER")
    mongo_password: str | None = Field(default=None, validation_alias="MONGO_PASSWORD")
    mongo_auth_source: str = Field(default="admin", validation_alias="MONGO_AUTH_SOURCE")
    mongo_db: str = Field(default="dblp", validation_alias="MONGO_DB")
    mongo_collection: str = Field(default="publications", validation_alias="MONGO_COLLECTION")

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
    )

settings = Settings()