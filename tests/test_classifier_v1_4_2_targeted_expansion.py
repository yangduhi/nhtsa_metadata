import csv
from pathlib import Path

from nhtsa_metadata.services.classification_accounting import (
    compute_accounting_metrics,
    gap_resolution_counts,
    read_classification_fixture,
)

FIXTURE_DIR = Path("tests/fixtures/classification")
STAGE_K_TEST_NOS = {"15517", "15518", "15519", "15528", "15531", "15532", "15534", "15539", "15540"}


def _rows(name: str) -> list[dict[str, str]]:
    with (FIXTURE_DIR / name).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_v1_4_2_canonical_registry_absorbs_only_28_target_rows() -> None:
    rows = _rows("canonical_label_registry_v1_4_2.csv")

    assert {row["source_proposed_rule_id"] for row in rows} == {
        "NEEDS_REAR_HYDROGEN_FUEL_CELL_IMPACTOR_RESEARCH_LABEL",
        "NEEDS_RESEARCH_FRONTAL_RIGID_BARRIER_30DEG_LABEL",
        "NEEDS_RESEARCH_OR_HIGH_SPEED_FMVSS214_SIDE_MDB_LABEL",
    }
    assert sum(int(row["absorbed_row_count"]) for row in rows) == 28
    assert {row["acceptance_status"] for row in rows} == {"accepted_targeted_v1_4_2"}


def test_v1_4_2_accounting_metrics_reach_target_without_forcing_noncanonical_rows() -> None:
    evidence_rows = read_classification_fixture(
        FIXTURE_DIR / "classification_evidence_v1_4_2.csv"
    )
    metrics = compute_accounting_metrics(evidence_rows, known_false_positive_count=0)

    assert metrics.total_count == 3900
    assert metrics.canonical_label_classified_count == 3881
    assert metrics.adjudicated_noncanonical_count == 19
    assert metrics.unadjudicated_count == 0
    assert metrics.known_false_positive_count == 0
    assert metrics.accounted_for_count == 3900
    assert metrics.disposition_status_counts == {
        "canonical_label_assigned": 3881,
        "out_of_scope_for_current_taxonomy": 6,
        "source_payload_anomaly": 2,
        "true_metadata_gap": 11,
    }


def test_v1_4_2_remaining_gap_triage_keeps_only_noncanonical_final_dispositions() -> None:
    rows = read_classification_fixture(FIXTURE_DIR / "classification_gap_triage_v1_4_2.csv")

    assert len(rows) == 19
    assert gap_resolution_counts(rows) == {
        "out_of_scope_for_current_taxonomy": 6,
        "source_payload_anomaly": 2,
        "true_metadata_gap": 11,
    }


def test_v1_4_2_acceptance_and_regression_checks_pass() -> None:
    acceptance = _rows("classification_acceptance_v1_4_2.csv")
    summary = {row["metric"]: row for row in _rows("classification_summary_v1_4_2.csv")}

    assert acceptance
    assert {row["status"] for row in acceptance} == {"pass"}
    assert summary["total_count"]["v1_4_2"] == "3900"
    assert summary["canonical_label_classified_count"]["v1_4_2"] == "3881"
    assert summary["adjudicated_noncanonical_count"]["v1_4_2"] == "19"
    assert summary["accounted_for_count"]["v1_4_2"] == "3900"
    assert summary["requires_new_canonical_label"]["v1_4_2"] == "0"
    assert int(summary["fallback_used_count"]["v1_4_2"]) <= int(
        summary["fallback_used_count"]["v1_4_1"]
    )
    assert int(summary["generic_used_count"]["v1_4_2"]) <= int(
        summary["generic_used_count"]["v1_4_1"]
    )


def test_v1_4_2_stage_k_refresh_rows_are_promoted() -> None:
    rows = read_classification_fixture(FIXTURE_DIR / "classification_evidence_v1_4_2.csv")
    by_test_no = {row["canonical_test_uid"].rsplit(":", maxsplit=1)[-1]: row for row in rows}

    assert STAGE_K_TEST_NOS <= set(by_test_no)
    for test_no in STAGE_K_TEST_NOS:
        row = by_test_no[test_no]
        assert row["final_status"] == "classified"
        assert row["final_label"]
        assert row["source_payload_ids"] != "[]"
        assert row["positive_evidence_json"] not in ("", "{}")
