from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from pathlib import Path

from alembic import command
from sqlalchemy import create_engine, inspect

from nhtsa_metadata.db.migrations import alembic_config, upgrade_head

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_SCHEMA = REPO_ROOT / "data" / "schema"
DOCS_SCHEMA = REPO_ROOT / "docs" / "schema"
LOCK_PATH = DATA_SCHEMA / "stage_f_schema_artifact_registry_2011plus_2026-04-30.lock"
MIGRATION_PATH = REPO_ROOT / "migrations" / "0003_schema_contract_v1_5.sql"
CLASSIFICATION_EVIDENCE_LINEAGE_COLUMNS = {
    "id",
    "source_system",
    "canonical_test_uid",
    "test_no",
    "classifier_version",
    "evidence_stage",
    "source_payload_id",
    "source_endpoint_name",
    "source_field_path",
    "normalized_feature_key",
    "candidate_rule_id",
    "final_status",
    "disposition_status",
    "evidence_json",
}
CLASSIFICATION_EVIDENCE_COMPATIBILITY_COLUMNS = {
    "classification_rule_id",
    "classification_label",
    "evidence_status",
    "endpoint_name",
    "field_catalog_id",
    "json_path",
    "evidence_value",
    "provenance_json",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _csv_row(rows: list[dict[str, str]], audit_id: str) -> dict[str, str]:
    for row in rows:
        if row["audit_id"] == audit_id:
            return row
    raise AssertionError(f"missing audit row: {audit_id}")


def test_schema_contract_v1_5_artifacts_are_registered() -> None:
    required_paths = {
        "docs/schema/schema_contract_v1_5.md",
        "docs/schema/endpoint_entity_matrix_v1_5.md",
        "docs/schema/field_catalog_v1_5.md",
        "docs/schema/code_value_contract_v1_5.md",
        "docs/schema/relationship_matrix_v1_5.md",
        "docs/phase_reports/stage_f_schema_contract_2011plus_2026-04-30.md",
        "data/schema/field_catalog_v1_5.csv",
        "data/schema/endpoint_entity_matrix_v1_5.csv",
        "data/schema/code_sets_v1_5.csv",
        "data/schema/code_values_v1_5.csv",
        "data/schema/relationship_matrix_v1_5.csv",
        "data/schema/schema_audit_v1_5.csv",
        "migrations/0003_schema_contract_v1_5.sql",
        "tests/test_schema_contract_v1_5.py",
        "scripts/build_schema_contract_v1_5.py",
    }

    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    assert lock["schema_version"] == "1.5"
    assert (
        lock["source"]["manifest_sha256"]
        == "b4a1262938d33793bff0d4aca78222e4bab51c7253d4084fbb80597096abe6be"
    )
    registered = {item["path"]: item for item in lock["artifacts"]}
    assert required_paths <= set(registered)

    for relative_path in required_paths:
        path = REPO_ROOT / relative_path
        assert path.exists(), relative_path
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert registered[relative_path]["sha256"] == digest
        assert path.suffix.lower() not in {".sqlite", ".db", ".zip", ".bin"}


def test_schema_contract_v1_5_csv_contracts_and_audit_result() -> None:
    field_rows = _read_csv(DATA_SCHEMA / "field_catalog_v1_5.csv")
    assert field_rows
    assert {
        "source_system",
        "endpoint_name",
        "entity_type",
        "raw_field_name",
        "normalized_field_name",
        "json_path",
        "observed_data_type",
        "contract_data_type",
        "nullable_observed",
        "is_code",
        "code_set_name",
        "first_seen_payload_id",
        "last_seen_payload_id",
        "occurrence_count",
        "contract_status",
        "exception_reason",
    } <= set(field_rows[0])
    assert all(row["source_system"] == "nhtsa_crash" for row in field_rows)

    code_sets = _read_csv(DATA_SCHEMA / "code_sets_v1_5.csv")
    code_values = _read_csv(DATA_SCHEMA / "code_values_v1_5.csv")
    assert len(code_sets) == 17
    assert len(code_values) == 757

    audit_rows = _read_csv(DATA_SCHEMA / "schema_audit_v1_5.csv")
    baseline = _csv_row(audit_rows, "audit_1_source_baseline_verification")
    assert baseline["status"] == "pass"
    assert baseline["hard_failures"] == "0"
    assert "manifest_rows=3891" in baseline["actual"]
    assert "source_payloads=66318" in baseline["actual"]

    json_paths = _csv_row(audit_rows, "audit_3_observed_json_path_coverage")
    assert json_paths["status"] == "pass"
    assert "unknown_observed_field_count=0" in json_paths["actual"]

    code_linkage = _csv_row(audit_rows, "audit_4_code_linkage")
    assert code_linkage["status"] in {"pass", "documented_exception"}
    assert "unlinked_code_field_hard_failures=0" in code_linkage["actual"]

    orphan = _csv_row(audit_rows, "audit_5_orphan_entity")
    assert orphan["status"] == "pass"
    assert "orphan_entity_count=0" in orphan["actual"]


def test_schema_contract_v1_5_sql_migration_is_additive(tmp_path: Path) -> None:
    database_path = tmp_path / "migration.sqlite"
    upgrade_head(f"sqlite:///{database_path}")

    con = sqlite3.connect(database_path)
    try:
        before_tables = {
            row[0]
            for row in con.execute(
                "select name from sqlite_master where type='table' order by name"
            )
        }
        before_source_payloads_columns = [
            row[1] for row in con.execute("pragma table_info(source_payloads)")
        ]
        before_code_values_columns = [
            row[1] for row in con.execute("pragma table_info(code_values)")
        ]

        con.executescript(MIGRATION_PATH.read_text(encoding="utf-8"))

        after_tables = {
            row[0]
            for row in con.execute(
                "select name from sqlite_master where type='table' order by name"
            )
        }
        assert before_tables <= after_tables
        assert {
            "schema_versions",
            "source_systems",
            "endpoint_requests",
            "manifest_tests",
            "test_identities",
            "entity_instances",
            "field_catalog",
            "field_occurrences",
            "code_sets",
            "relationship_edges",
            "semantic_concepts",
            "classification_rules",
            "classification_evidence",
            "audit_results",
        } <= after_tables
        assert before_source_payloads_columns == [
            row[1] for row in con.execute("pragma table_info(source_payloads)")
        ]
        assert before_code_values_columns == [
            row[1] for row in con.execute("pragma table_info(code_values)")
        ]
    finally:
        con.close()


def test_schema_contract_v1_5_sql_uses_alembic_lineage_evidence_shape(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "contract.sqlite"
    con = sqlite3.connect(database_path)
    try:
        con.executescript(MIGRATION_PATH.read_text(encoding="utf-8"))
        columns = {
            row[1]: {"notnull": row[3]}
            for row in con.execute("pragma table_info(classification_evidence)")
        }
    finally:
        con.close()

    column_names = set(columns)
    assert CLASSIFICATION_EVIDENCE_LINEAGE_COLUMNS <= column_names
    assert CLASSIFICATION_EVIDENCE_COMPATIBILITY_COLUMNS <= column_names
    assert all(
        columns[column]["notnull"] == 0
        for column in CLASSIFICATION_EVIDENCE_COMPATIBILITY_COLUMNS
    )


def test_schema_contract_sql_before_alembic_head_preserves_lineage_evidence_shape(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "contract_before_head.sqlite"
    database_url = f"sqlite:///{database_path}"
    config = alembic_config(database_url)

    command.upgrade(config, "0003_classification_disposition")
    con = sqlite3.connect(database_path)
    try:
        con.executescript(MIGRATION_PATH.read_text(encoding="utf-8"))
    finally:
        con.close()
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    columns = {column["name"] for column in inspect(engine).get_columns("classification_evidence")}
    assert CLASSIFICATION_EVIDENCE_LINEAGE_COLUMNS <= columns
