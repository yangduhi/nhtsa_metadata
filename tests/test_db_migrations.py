from sqlalchemy import create_engine, inspect

from nhtsa_metadata.db.migrations import downgrade_base, upgrade_head


def test_alembic_upgrade_and_downgrade(tmp_path) -> None:  # type: ignore[no-untyped-def]
    database_url = f"sqlite:///{tmp_path / 'migration.sqlite'}"
    upgrade_head(database_url)
    engine = create_engine(database_url)
    assert "source_payloads" in inspect(engine).get_table_names()
    assert "tests" in inspect(engine).get_table_names()

    downgrade_base(database_url)
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
