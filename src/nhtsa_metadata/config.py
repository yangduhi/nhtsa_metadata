from datetime import date
from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

from nhtsa_metadata.constants import (
    APP_NAME,
    DEFAULT_ALLOW_LIVE,
    DEFAULT_DATABASE_URL,
    DEFAULT_DOWNLOAD_DIR,
    DEFAULT_ENVIRONMENT,
    DEFAULT_MAX_DOWNLOAD_BYTES,
    DEFAULT_MIN_TEST_DATE,
    DEFAULT_NHTSA_BASE_URL,
    DEFAULT_RATE_LIMIT_DELAY_SECONDS,
    DEFAULT_RETRY_COUNT,
    DEFAULT_TIMEOUT_SECONDS,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NHTSA_METADATA_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = APP_NAME
    environment: str = DEFAULT_ENVIRONMENT
    database_url: str = DEFAULT_DATABASE_URL
    nhtsa_base_url: str = DEFAULT_NHTSA_BASE_URL
    allow_live: bool = DEFAULT_ALLOW_LIVE
    default_timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    default_retry_count: int = DEFAULT_RETRY_COUNT
    rate_limit_delay_seconds: float = DEFAULT_RATE_LIMIT_DELAY_SECONDS
    min_test_date: date = DEFAULT_MIN_TEST_DATE
    download_dir: str = DEFAULT_DOWNLOAD_DIR
    max_download_bytes: int = DEFAULT_MAX_DOWNLOAD_BYTES
    reference_database_path: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "reference_database_path",
            "NHTSA_METADATA_REFERENCE_DB_PATH",
            "NHTSA_METADATA_REFERENCE_DATABASE_PATH",
        ),
    )


def sanitize_database_url(database_url: str) -> str:
    """Render a database URL without credentials."""
    return make_url(database_url).render_as_string(hide_password=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
