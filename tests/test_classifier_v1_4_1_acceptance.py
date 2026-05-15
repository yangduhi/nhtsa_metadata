import csv
from pathlib import Path

DATA_DIR = Path("tests/fixtures/classification")
ALLOWED_GAP_RESOLUTIONS = {
    "classified_by_specific_rule",
    "classified_by_negative_disambiguation",
    "true_metadata_gap",
    "out_of_scope_for_current_taxonomy",
    "requires_new_canonical_label",
    "source_payload_anomaly",
}


def _rows(name: str) -> list[dict[str, str]]:
    with (DATA_DIR / name).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_v1_4_1_acceptance_hard_requirements() -> None:
    rows = _rows("classification_acceptance_v1_4_1.csv")
    assert rows
    assert {row["status"] for row in rows} == {"pass"}

    checks = {row["check"]: row for row in rows}
    assert checks["total manifest rows"]["actual"] == "3891"
    assert checks["missing tests"]["actual"] == "0"
    assert checks["classification live API used"]["actual"] == "0"
    assert checks["known false-positive hard cases"]["actual"] == "0"
    assert checks["side pole over-confirmed"]["actual"] == "0"
    assert checks["sled classified as full vehicle crash"]["actual"] == "0"
    assert checks["original 47 unclassified all adjudicated"]["actual"] == "47"
    assert checks["classification evidence rows"]["actual"] == "3891"
    assert checks["classification without evidence rows"]["actual"] == "0"
    assert checks["source evidence missing positive classifications"]["actual"] == "0"


def test_v1_4_1_original_gap_triage_is_complete() -> None:
    rows = _rows("classification_gap_triage_v1_4_1.csv")
    assert len(rows) == 47
    assert {row["proposed_resolution"] for row in rows} <= ALLOWED_GAP_RESOLUTIONS
    assert all(row["canonical_test_uid"] for row in rows)
    assert all(row["blocking_missing_fields"] for row in rows)
    assert all(row["endpoint_evidence"] for row in rows)
    assert all(row["adjudication_note"] for row in rows)


def test_v1_4_1_known_false_positive_triage_is_repaired() -> None:
    rows = _rows("known_false_positive_triage_v1_4_1.csv")
    assert len(rows) == 26
    family_counts = {}
    for row in rows:
        family_counts[row["false_positive_family"]] = (
            family_counts.get(row["false_positive_family"], 0) + 1
        )
        assert row["acceptance_status"].startswith("accepted")
        assert row["negative_evidence_ignored_by_v1_4"]
        assert row["corrected_label_or_status"]

    assert family_counts == {
        "side_pole_over_confirmed": 8,
        "sled_full_vehicle_false_positive": 18,
    }


def test_v1_4_1_evidence_rows_cover_all_final_classifications() -> None:
    rows = _rows("classification_evidence_v1_4_1.csv")
    assert len(rows) == 3891
    classified = [row for row in rows if row["final_status"] == "classified"]
    assert classified
    assert all(row["positive_evidence_json"] for row in classified)
    assert all(row["source_payload_ids"] != "[]" for row in classified)
    assert all(row["source_endpoints"] != "[]" for row in classified)


def test_v1_4_1_quality_counts_do_not_expand_fallback_or_generic() -> None:
    rows = {row["metric"]: row for row in _rows("classification_summary_v1_4_1.csv")}
    assert int(rows["fallback_used_count"]["v1_4_1"]) <= int(rows["fallback_used_count"]["v1_4"])
    assert int(rows["generic_used_count"]["v1_4_1"]) <= int(rows["generic_used_count"]["v1_4"])
    assert int(rows["known_false_positive_count"]["v1_4_1"]) == 0
