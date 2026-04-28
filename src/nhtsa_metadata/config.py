from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NHTSA_METADATA_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "nhtsa_metadata"
    environment: str = "local"
    database_url: str = "sqlite:///data/nhtsa_metadata.sqlite"
    nhtsa_base_url: str = "https://nrd.api.nhtsa.dot.gov/nhtsa/vehicle/api/v1"
    allow_live: bool = False
    default_timeout_seconds: float = 30.0
    default_retry_count: int = 2
    rate_limit_delay_seconds: float = 0.0


def sanitize_database_url(database_url: str) -> str:
    """Render a database URL without credentials."""
    return make_url(database_url).render_as_string(hide_password=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
