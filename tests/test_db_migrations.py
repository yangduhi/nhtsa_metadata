from sqlalchemy import create_engine, inspect

from nhtsa_metadata.db.migrations import downgrade_base, upgrade_head


def test_alembic_upgrade_and_downgrade(tmp_path) -> None:  # type: ignore[no-untyped-def]
    database_url = f"sqlite:///{tmp_path / 'migration.sqlite'}"
    upgrade_head(database_url)
    engine = create_engine(database_url)
    table_names = inspect(engine).get_table_names()
    assert "source_payloads" in table_names
    assert "tests" in table_names
    assert "discovery_runs" in table_names
    assert "discovery_manifest_rows" in table_names
    assert "discovery_authority_decisions" in table_names
    assert "classification_adjudication" in table_names
    assert "test_classification_candidates" in table_names

    unique_constraints = inspect(engine).get_unique_constraints("discovery_manifest_rows")
    unique_sets = {tuple(item["column_names"]) for item in unique_constraints}
    assert ("discovery_run_id", "test_no") in unique_sets
    assert ("discovery_run_id", "row_hash") in unique_sets

    classification_columns = {
        column["name"] for column in inspect(engine).get_columns("test_classification")
    }
    assert {
        "classification_status",
        "disposition_status",
        "canonical_label",
        "canonical_rule_id",
        "classification_run_id",
    } <= classification_columns

    downgrade_base(database_url)
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
