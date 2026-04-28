from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from nhtsa_metadata.config import Settings, get_settings


def create_engine_for_settings(settings: Settings | None = None) -> Engine:
    effective_settings = settings or get_settings()
    return create_engine(effective_settings.database_url, future=True)


def create_session_factory(settings: Settings | None = None) -> sessionmaker[Session]:
    engine = create_engine_for_settings(settings)
    return sessionmaker(bind=engine, expire_on_commit=False)
