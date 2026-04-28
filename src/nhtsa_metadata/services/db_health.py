from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


@dataclass(frozen=True)
class DbHealth:
    ok: bool
    table_count: int
    migration_ready: bool


def check_db_health(engine: Engine) -> DbHealth:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    table_names = inspect(engine).get_table_names()
    return DbHealth(
        ok=True,
        table_count=len(table_names),
        migration_ready="source_payloads" in table_names and "tests" in table_names,
    )
