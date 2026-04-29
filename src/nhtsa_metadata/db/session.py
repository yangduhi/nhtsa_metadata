from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from nhtsa_metadata.config import Settings, get_settings
from nhtsa_metadata.db.models import Base


def create_engine_for_settings(settings: Settings | None = None) -> Engine:
    effective_settings = settings or get_settings()
    return create_engine(effective_settings.database_url, future=True)


def create_session_factory(settings: Settings | None = None) -> sessionmaker[Session]:
    engine = create_engine_for_settings(settings)
    return sessionmaker(bind=engine, expire_on_commit=False)


def ensure_schema(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_additive_columns(engine)


def drop_schema(engine: Engine) -> None:
    Base.metadata.drop_all(bind=engine)


def _ensure_additive_columns(engine: Engine) -> None:
    """Keep local SQLite validation DBs compatible with additive model changes."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    additions = {
        "restraints": {
            "semantic_key": "TEXT NOT NULL DEFAULT ''",
            "semantic_hash": "VARCHAR(64) NOT NULL DEFAULT ''",
        },
        "media_assets": {
            "asset_subtype": "VARCHAR(64)",
        },
    }
    with engine.begin() as connection:
        for table_name, columns in additions.items():
            if table_name not in tables:
                continue
            existing = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, ddl in columns.items():
                if column_name not in existing:
                    connection.execute(
                        text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}")
                    )
