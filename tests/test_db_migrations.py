from alembic import command
from sqlalchemy import create_engine, inspect

from nhtsa_metadata.db.migrations import alembic_config, downgrade_base, upgrade_head


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
    assert "barrier_load_cell_classification" in table_names
    assert "barrier_load_cell_channel_map" in table_names

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
    vehicle_columns = {column["name"] for column in inspect(engine).get_columns("vehicles")}
    assert {
        "body_type",
        "curb_weight_raw",
        "curb_weight",
        "vehicle_length_raw",
        "vehicle_length",
        "vehicle_width_raw",
        "vehicle_width",
        "wheelbase_raw",
        "wheelbase",
        "vax_crush_distance_raw",
        "vax_crush_distance",
    } <= vehicle_columns
    summary_columns = {
        column["name"] for column in inspect(engine).get_columns("test_filter_summary")
    }
    assert {
        "vehicle_test_weight_min",
        "vehicle_test_weight_max",
        "curb_weight_min",
        "curb_weight_max",
        "vehicle_length_min",
        "vehicle_length_max",
        "vehicle_width_min",
        "vehicle_width_max",
        "wheelbase_min",
        "wheelbase_max",
        "vax_crush_distance_min",
        "vax_crush_distance_max",
        "has_load_cell_barrier",
        "load_cell_barrier_classification_ids_json",
        "load_cell_barrier_families_json",
        "load_cell_barrier_config_version",
        "load_cell_barrier_channel_count",
        "load_cell_barrier_force_channel_count",
        "load_cell_barrier_moment_channel_count",
    } <= summary_columns
    load_cell_columns = {
        column["name"]
        for column in inspect(engine).get_columns("barrier_load_cell_classification")
    }
    assert {
        "test_no",
        "config_version",
        "classification_id",
        "normalized_barrier_shape_key",
        "shape_alias_rule_id",
        "channel_count",
        "force_channel_count",
        "moment_channel_count",
    } <= load_cell_columns

    downgrade_base(database_url)
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}


def test_alembic_upgrades_existing_sqlite_database_from_0002_to_head(tmp_path) -> None:  # type: ignore[no-untyped-def]
    database_url = f"sqlite:///{tmp_path / 'existing.sqlite'}"
    config = alembic_config(database_url)

    command.upgrade(config, "0002_discovery_provenance")
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    assert "classification_adjudication" in inspect(engine).get_table_names()
    candidate_unique_constraints = inspect(engine).get_unique_constraints(
        "test_classification_candidates"
    )
    candidate_unique_sets = {tuple(item["column_names"]) for item in candidate_unique_constraints}
    assert ("test_no", "classifier_version", "rank") in candidate_unique_sets


def test_alembic_upgrades_legacy_sqlite_database_stamped_at_0002_to_head(tmp_path) -> None:  # type: ignore[no-untyped-def]
    database_path = tmp_path / "legacy.sqlite"
    database_url = f"sqlite:///{database_path}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE tests (id INTEGER PRIMARY KEY)")
        connection.exec_driver_sql("CREATE TABLE source_payloads (id INTEGER PRIMARY KEY)")
        connection.exec_driver_sql("CREATE TABLE test_classification (id INTEGER PRIMARY KEY)")

    config = alembic_config(database_url)
    command.stamp(config, "0002_discovery_provenance")
    command.upgrade(config, "head")

    inspector = inspect(engine)
    assert "classification_adjudication" in inspector.get_table_names()
    assert "test_classification_candidates" in inspector.get_table_names()
