from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_AUDIT = REPO_ROOT / "data" / "schema" / "schema_audit_v1_5.csv"
CLASSIFICATION_DIR = REPO_ROOT / "data" / "classification"
INTEGRATION_REPORT = (
    REPO_ROOT
    / "docs"
    / "phase_reports"
    / "stage_f_integration_acceptance_2011plus_2026-04-30.md"
)
INTEGRATION_REGISTRY = (
    REPO_ROOT / "data" / "stage_f_integration_artifact_registry_2011plus_2026-04-30.lock"
)
EXPECTED_MANIFEST_SHA256 = (
    "b4a1262938d33793bff0d4aca78222e4bab51c7253d4084fbb80597096abe6be"
)
EVIDENCE_COLUMNS = [
    "canonical_test_uid",
    "classifier_version",
    "final_label",
    "final_status",
    "confidence",
    "rule_id",
    "rule_family",
    "positive_evidence_json",
    "negative_evidence_json",
    "source_payload_ids",
    "source_endpoints",
    "source_field_paths",
    "adjudication_status",
    "adjudication_note",
]
ADJUDICATED_FINAL_STATUSES = {
    "true_metadata_gap",
    "out_of_scope_for_current_taxonomy",
    "requires_new_canonical_label",
    "source_payload_anomaly",
}
FORBIDDEN_SUFFIXES = {".sqlite", ".db", ".zip", ".bin", ".mp4", ".avi", ".mov"}


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _by_key(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    return {row[key]: row for row in rows}


def test_stage_f_schema_baseline_and_exception_breakdown() -> None:
    audit = _by_key(_rows(SCHEMA_AUDIT), "audit_id")
    baseline = audit["audit_1_source_baseline_verification"]
    assert baseline["status"] == "pass"
    assert baseline["hard_failures"] == "0"
    for expected in [
        "manifest_rows=3891",
        "collected_tests=3891",
        "missing_tests=0",
        "source_payloads=66318",
        "observations=66318",
        "code_sets=17",
        "code_values=757",
        f"manifest_hash={EXPECTED_MANIFEST_SHA256}",
    ]:
        assert expected in baseline["actual"]

    assert sum(int(row["hard_failures"]) for row in audit.values()) == 0
    assert sum(int(row["documented_exceptions"]) for row in audit.values()) == 455
    assert audit["audit_2_endpoint_to_entity_coverage"]["documented_exceptions"] == "10"
    assert audit["audit_3_observed_json_path_coverage"]["documented_exceptions"] == "420"
    assert audit["audit_4_code_linkage"]["documented_exceptions"] == "25"
    assert audit["audit_7_migration_sanity"]["status"] == "pass"


def test_stage_f_integration_artifacts_are_registered() -> None:
    required_paths = {
        "docs/phase_reports/stage_f_integration_acceptance_2011plus_2026-04-30.md",
        "docs/phase_reports/stage_f_schema_contract_2011plus_2026-04-30.md",
        "docs/phase_reports/stage_f_classification_acceptance_2011plus_2026-04-30.md",
        "docs/schema/schema_contract_v1_5.md",
        "data/schema/field_catalog_v1_5.csv",
        "data/schema/endpoint_entity_matrix_v1_5.csv",
        "data/schema/code_sets_v1_5.csv",
        "data/schema/code_values_v1_5.csv",
        "data/schema/relationship_matrix_v1_5.csv",
        "data/schema/schema_audit_v1_5.csv",
        "data/classification/classification_gap_triage_v1_4_1.csv",
        "data/classification/known_false_positive_triage_v1_4_1.csv",
        "data/classification/classification_evidence_v1_4_1.csv",
        "data/classification/classification_summary_v1_4_1.csv",
        "data/classification/classification_acceptance_v1_4_1.csv",
        "migrations/0003_schema_contract_v1_5.sql",
        "scripts/classifier_v1_4_1_acceptance.py",
        "tests/test_stage_f_integration_acceptance.py",
    }
    registry = json.loads(INTEGRATION_REGISTRY.read_text(encoding="utf-8"))
    assert registry["integration_version"] == "stage_f_schema_v1_5_classifier_v1_4_1"
    assert registry["source"]["manifest_sha256"] == EXPECTED_MANIFEST_SHA256
    assert registry["source"]["manifest_rows"] == 3891
    assert registry["source"]["source_payloads"] == 66318
    assert registry["source"]["payload_observations"] == 66318
    assert registry["source"]["code_sets"] == 17
    assert registry["source"]["code_values"] == 757

    registered = {item["path"]: item for item in registry["artifacts"]}
    assert required_paths <= set(registered)
    for relative_path in required_paths:
        path = REPO_ROOT / relative_path
        assert path.exists(), relative_path
        assert registered[relative_path]["sha256"] == _sha256(path)
        assert registered[relative_path]["bytes"] == path.stat().st_size
        assert path.suffix.lower() not in FORBIDDEN_SUFFIXES
        if relative_path.startswith("data/schema/") or relative_path.startswith(
            "data/classification/"
        ):
            assert registered[relative_path]["tracked_with_force"] is True


def test_classifier_v1_4_1_acceptance_and_exit_semantics() -> None:
    acceptance = _by_key(
        _rows(CLASSIFICATION_DIR / "classification_acceptance_v1_4_1.csv"), "check"
    )
    assert {row["status"] for row in acceptance.values()} == {"pass"}
    assert acceptance["total manifest rows"]["actual"] == "3891"
    assert acceptance["missing tests"]["actual"] == "0"
    assert acceptance["classification live API used"]["actual"] == "0"
    assert acceptance["package/media/file download"]["actual"] == "0"
    assert acceptance["known false-positive hard cases"]["actual"] == "0"
    assert acceptance["side pole over-confirmed"]["actual"] == "0"
    assert acceptance["sled classified as full vehicle crash"]["actual"] == "0"
    assert acceptance["original 47 unclassified all adjudicated"]["actual"] == "47"
    assert acceptance["classification without evidence rows"]["actual"] == "0"
    assert acceptance["source evidence missing positive classifications"]["actual"] == "0"

    summary = _by_key(_rows(CLASSIFICATION_DIR / "classification_summary_v1_4_1.csv"), "metric")
    assert int(summary["fallback_used_count"]["v1_4_1"]) == 845
    assert int(summary["fallback_used_count"]["v1_4"]) == 852
    assert int(summary["generic_used_count"]["v1_4_1"]) == 565
    assert int(summary["generic_used_count"]["v1_4"]) == 572
    assert summary["multi_candidate_count"]["delta"] == "6"
    assert summary["multi_rule_family_count"]["delta"] == "4"

    gap_rows = _rows(CLASSIFICATION_DIR / "classification_gap_triage_v1_4_1.csv")
    assert len(gap_rows) == 47
    assert Counter(row["proposed_resolution"] for row in gap_rows) == {
        "requires_new_canonical_label": 28,
        "true_metadata_gap": 11,
        "out_of_scope_for_current_taxonomy": 6,
        "source_payload_anomaly": 2,
    }

    false_positive_rows = _rows(
        CLASSIFICATION_DIR / "known_false_positive_triage_v1_4_1.csv"
    )
    assert len(false_positive_rows) == 26
    assert Counter(row["false_positive_family"] for row in false_positive_rows) == {
        "side_pole_over_confirmed": 8,
        "sled_full_vehicle_false_positive": 18,
    }
    assert all(row["acceptance_status"].startswith("accepted") for row in false_positive_rows)

    report = INTEGRATION_REPORT.read_text(encoding="utf-8")
    assert "v1.4 baseline hard fail behavior is preserved" in report
    assert "authoritative v1.4.1 acceptance signal returns exit 0" in report
    assert "legacy full-corpus CLI exit 1 is non-authoritative" in report


def test_classification_evidence_contract_mapping_and_coverage() -> None:
    with (CLASSIFICATION_DIR / "classification_evidence_v1_4_1.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == EVIDENCE_COLUMNS
        evidence_rows = list(reader)
    assert len(evidence_rows) == 3891

    report = INTEGRATION_REPORT.read_text(encoding="utf-8")
    for column in EVIDENCE_COLUMNS:
        assert f"| `{column}` |" in report

    classified = [row for row in evidence_rows if row["final_status"] == "classified"]
    assert len(classified) == 3844
    assert all(row["positive_evidence_json"] for row in classified)
    assert all(row["source_payload_ids"] != "[]" for row in classified)
    assert all(row["source_endpoints"] != "[]" for row in classified)
    assert all(row["source_field_paths"] != "[]" for row in classified)

    adjudicated = [row for row in evidence_rows if row["final_status"] != "classified"]
    assert len(adjudicated) == 47
    assert {row["final_status"] for row in adjudicated} == ADJUDICATED_FINAL_STATUSES
    assert all(row["adjudication_status"] == "adjudicated" for row in adjudicated)
    assert all(row["adjudication_note"] for row in adjudicated)
    assert all(row["source_payload_ids"] != "[]" for row in adjudicated)
    assert all(row["source_endpoints"] != "[]" for row in adjudicated)
    assert all(row["source_field_paths"] != "[]" for row in adjudicated)


def test_git_artifact_hygiene_and_migration_numbering() -> None:
    migrations = sorted(path.name for path in (REPO_ROOT / "migrations").glob("*.sql"))
    assert migrations == ["0003_schema_contract_v1_5.sql"]

    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert staged.returncode == 0
    staged_paths = [Path(line.strip()) for line in staged.stdout.splitlines() if line.strip()]
    assert all(path.suffix.lower() not in FORBIDDEN_SUFFIXES for path in staged_paths)

    report = INTEGRATION_REPORT.read_text(encoding="utf-8")
    assert "no .sqlite, .db, media, raw payload archive, or package download" in report
    assert "ignored data artifacts intentionally committed with -f" in report
