"""애플리케이션 설정 모듈.

Pydantic Settings를 사용하여 환경변수에서 설정을 로드합니다.
PostgreSQL, MongoDB, Elasticsearch, Redis, JWT 등의 설정을 관리합니다.
"""

from __future__ import annotations
from pathlib import Path
import os
from typing import Sequence
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _base_dir() -> Path:
    """프로젝트 루트 디렉토리 경로를 반환한다."""
    return Path(__file__).resolve().parents[2]


def _env_files() -> Sequence[Path]:
    """로드할 환경변수 파일 목록을 반환한다.

    APP_ENV 환경변수 값에 따라 적절한 .env 파일 경로들을
    우선순위 순서로 반환합니다.

    Returns:
        존재하는 환경변수 파일 경로 시퀀스.
    """
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
    """애플리케이션 설정 클래스.

    환경변수에서 설정값을 로드하여 타입 안전한 설정 객체를 제공합니다.

    Attributes:
        app_env: 애플리케이션 환경 (local, dev, prod).
        db_host: PostgreSQL 호스트.
        db_port: PostgreSQL 포트.
        db_user: PostgreSQL 사용자.
        db_password: PostgreSQL 비밀번호.
        db_name: PostgreSQL 데이터베이스명.
        mongo_host: MongoDB 호스트.
        mongo_port: MongoDB 포트.
        mongo_db: MongoDB 데이터베이스명.
        mongo_collection: MongoDB 컬렉션명.
        es_host: Elasticsearch 호스트.
        es_port: Elasticsearch 포트.
        summary_server_url: GPU 서버 URL.
        redis_host: Redis 호스트.
        redis_port: Redis 포트.
        secret_key: JWT 시크릿 키.
        jwt_algorithm: JWT 알고리즘.
        access_token_expire_minutes: 액세스 토큰 만료 시간(분).
    """

    app_env: str = Field(default="local", validation_alias="APP_ENV")

    db_host: str = Field(default="localhost", validation_alias="POSTGRES_HOST")
    db_port: int = Field(default=5432, validation_alias="POSTGRES_PORT")
    db_user: str = Field(default="postgres", validation_alias="POSTGRES_USER")
    db_password: str = Field(default="", validation_alias="POSTGRES_PASSWORD")
    db_name: str = Field(default="app", validation_alias="POSTGRES_DB")



    mongo_host: str = Field(default="localhost", validation_alias="MONGO_HOST")
    mongo_port: int = Field(default=27017, validation_alias="MONGO_PORT")
    mongo_user: str | None = Field(default=None, validation_alias="MONGO_USER")
    mongo_password: str | None = Field(default=None, validation_alias="MONGO_PASSWORD")
    mongo_auth_source: str = Field(
        default="admin", validation_alias="MONGO_AUTH_SOURCE"
    )
    mongo_db: str = Field(default="arxiv", validation_alias="MONGO_DB")
    mongo_collection: str = Field(default="papers", validation_alias="MONGO_COLLECTION")



    prod_mongo_host: str | None = Field(
        default=None, validation_alias="PROD_MONGO_HOST"
    )
    prod_mongo_port: int = Field(default=27017, validation_alias="PROD_MONGO_PORT")
    prod_mongo_user: str | None = Field(
        default=None, validation_alias="PROD_MONGO_USER"
    )
    prod_mongo_password: str | None = Field(
        default=None, validation_alias="PROD_MONGO_PASSWORD"
    )
    prod_mongo_auth_source: str = Field(
        default="admin", validation_alias="PROD_MONGO_AUTH_SOURCE"
    )
    prod_mongo_db: str = Field(default="arxiv", validation_alias="PROD_MONGO_DB")
    prod_mongo_collection: str = Field(
        default="arxiv_papers", validation_alias="PROD_MONGO_COLLECTION"
    )



    es_host: str = Field(default="localhost", validation_alias="ES_HOST")
    es_port: int = Field(default=9200, validation_alias="ES_PORT")
    es_user: str | None = Field(default=None, validation_alias="ES_USER")
    es_password: str | None = Field(default=None, validation_alias="ES_PASSWORD")
    es_use_ssl: bool = Field(default=False, validation_alias="ES_USE_SSL")
    es_index_name: str = Field(default="papers", validation_alias="ES_INDEX_NAME")

    summary_server_url: str = Field(
        default="http://localhost:8000", validation_alias="GPU_SERVER"
    )

    # GPU 요약 서버 재시도 설정
    summary_request_timeout: int = Field(
        default=600, validation_alias="SUMMARY_REQUEST_TIMEOUT"
    )
    summary_retry_max_attempts: int = Field(
        default=5, validation_alias="SUMMARY_RETRY_MAX_ATTEMPTS"
    )
    summary_retry_initial_delay: float = Field(
        default=2.0, validation_alias="SUMMARY_RETRY_INITIAL_DELAY"
    )
    summary_retry_max_delay: float = Field(
        default=60.0, validation_alias="SUMMARY_RETRY_MAX_DELAY"
    )
    summary_batch_size: int = Field(
        default=10, validation_alias="SUMMARY_BATCH_SIZE"
    )
    summary_batch_delay: float = Field(
        default=1.0, validation_alias="SUMMARY_BATCH_DELAY"
    )
    summary_retry_batch_size: int = Field(
        default=1, validation_alias="SUMMARY_RETRY_BATCH_SIZE"
    )

    redis_host: str = Field(default="localhost", validation_alias="REDIS_HOST")
    redis_port: int = Field(default=6379, validation_alias="REDIS_PORT")
    redis_db: int = Field(default=0, validation_alias="REDIS_DB")





    secret_key: str = Field(default="change-me-in-prod", validation_alias="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=60, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
        env_ignore_empty=True,
    )


settings = Settings()
