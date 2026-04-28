from pathlib import Path

from alembic import command
from alembic.config import Config


def alembic_config(database_url: str, repo_root: Path | None = None) -> Config:
    root = repo_root or Path(__file__).resolve().parents[3]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def upgrade_head(database_url: str) -> None:
    command.upgrade(alembic_config(database_url), "head")


def downgrade_base(database_url: str) -> None:
    command.downgrade(alembic_config(database_url), "base")
