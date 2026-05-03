from pathlib import Path

from sqlalchemy import create_engine, inspect

from nhtsa_metadata.db.migrations import upgrade_head
from nhtsa_metadata.services.classification_accounting import read_classification_fixture
from nhtsa_metadata.services.classification_lineage import (
    build_lineage_audit_rows,
    compute_lineage_metrics,
    read_lineage_audit,
)

FIXTURE_DIR = Path("tests/fixtures/classification")


def test_schema_v1_6_lineage_tables_are_in_migration_head(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'lineage.sqlite'}"
    upgrade_head(database_url)
    table_names = set(inspect(create_engine(database_url)).get_table_names())

    assert {
        "test_classification",
        "test_classification_candidates",
        "classification_evidence",
        "classification_adjudication",
        "canonical_label_registry",
        "rule_registry",
        "program_standard_evidence",
        "test_event_domain",
        "impact_device_evidence",
        "restraint_equipment_evidence",
        "classification_feature_evidence",
    } <= table_names


def test_schema_v1_6_fixture_lineage_is_complete_for_all_accounted_rows() -> None:
    audit_rows = read_lineage_audit(FIXTURE_DIR / "classification_lineage_audit_v1_6.csv")
    metrics = compute_lineage_metrics(audit_rows)

    assert metrics.total_count == 3891
    assert metrics.source_payload_linked_count == 3891
    assert metrics.normalized_feature_linked_count == 3891
    assert metrics.candidate_or_disposition_linked_count == 3891
    assert metrics.final_decision_linked_count == 3891
    assert metrics.complete_lineage_count == 3891
    assert metrics.missing_lineage_count == 0


def test_schema_v1_6_runtime_lineage_builder_matches_checked_in_audit_fixture() -> None:
    evidence_rows = read_classification_fixture(
        FIXTURE_DIR / "classification_evidence_v1_4_2.csv"
    )
    expected = read_lineage_audit(FIXTURE_DIR / "classification_lineage_audit_v1_6.csv")

    assert build_lineage_audit_rows(evidence_rows) == expected
