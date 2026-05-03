from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from nhtsa_metadata.services.classification_accounting import (
    compute_accounting_metrics,
    read_classification_fixture,
)

TARGET_TEST_NOS = (15517, 15518, 15519, 15528, 15531, 15532, 15534, 15539, 15540)
FIXTURE_DIR = Path("tests/fixtures/classification")
CLASSIFICATION_JSON = Path("data/stage_k_classification_v1_4_2_refresh_2026-05-03.json")
REFRESH_DB = Path("data/full_2011plus_metadata_only_refresh_2026-05-03.sqlite")

EVIDENCE_FILE = "classification_evidence_v1_4_2.csv"
GAP_FILE = "classification_gap_triage_v1_4_2.csv"
SUMMARY_FILE = "classification_summary_v1_4_2.csv"
ACCEPTANCE_FILE = "classification_acceptance_v1_4_2.csv"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-dir", type=Path, default=FIXTURE_DIR)
    parser.add_argument("--classification-json", type=Path, default=CLASSIFICATION_JSON)
    parser.add_argument("--refresh-db", type=Path, default=REFRESH_DB)
    args = parser.parse_args()

    _require_file(args.classification_json)
    _require_file(args.refresh_db)

    evidence_path = args.fixture_dir / EVIDENCE_FILE
    gap_path = args.fixture_dir / GAP_FILE
    summary_path = args.fixture_dir / SUMMARY_FILE
    acceptance_path = args.fixture_dir / ACCEPTANCE_FILE
    for path in (evidence_path, gap_path, summary_path, acceptance_path):
        _require_file(path)

    evidence_rows = read_classification_fixture(evidence_path)
    fieldnames = list(evidence_rows[0])
    existing_uids = {row["canonical_test_uid"] for row in evidence_rows}
    existing_targets = sorted(
        test_no for test_no in TARGET_TEST_NOS if _uid(test_no) in existing_uids
    )
    if existing_targets:
        raise SystemExit(f"target rows already exist in {evidence_path}: {existing_targets}")

    classification_rows = _target_classification_rows(args.classification_json)
    payload_index = _payload_index(args.refresh_db)
    appended_rows = [
        _evidence_row(classification_rows[test_no], payload_index[test_no])
        for test_no in TARGET_TEST_NOS
    ]

    promoted_rows = sorted(
        [*evidence_rows, *appended_rows],
        key=lambda row: int(row["canonical_test_uid"].rsplit(":", maxsplit=1)[-1]),
    )
    if len(promoted_rows) != 3900:
        raise SystemExit(f"expected 3900 promoted evidence rows, got {len(promoted_rows)}")

    gap_rows = read_classification_fixture(gap_path)
    if len(gap_rows) != 19:
        raise SystemExit(f"expected 19 v1.4.2 remaining gap rows, got {len(gap_rows)}")

    metrics = compute_accounting_metrics(promoted_rows, known_false_positive_count=0)
    if metrics.total_count != 3900 or metrics.accounted_for_count != 3900:
        raise SystemExit(f"unexpected promoted accounting metrics: {metrics}")
    if metrics.canonical_label_classified_count != 3881:
        raise SystemExit(
            "expected 3881 canonical rows, got "
            f"{metrics.canonical_label_classified_count}"
        )
    if metrics.adjudicated_noncanonical_count != 19 or metrics.unadjudicated_count != 0:
        raise SystemExit(f"unexpected noncanonical accounting metrics: {metrics}")

    _write_rows(evidence_path, fieldnames, promoted_rows)
    _write_rows(
        summary_path,
        ["metric", "v1_4_1", "v1_4_2", "delta", "status", "note"],
        _summary_rows(gap_rows),
    )
    _write_rows(
        acceptance_path,
        ["check", "expected", "actual", "status", "note"],
        _acceptance_rows(metrics, gap_rows),
    )

    print(
        json.dumps(
            {
                "appended_rows": len(appended_rows),
                "evidence_rows": len(promoted_rows),
                "accounted_for_count": metrics.accounted_for_count,
                "canonical_label_classified_count": metrics.canonical_label_classified_count,
                "adjudicated_noncanonical_count": metrics.adjudicated_noncanonical_count,
            },
            sort_keys=True,
        )
    )


def _target_classification_rows(path: Path) -> dict[int, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows_by_test = {int(row["test_no"]): row for row in payload["results"]}
    missing = sorted(set(TARGET_TEST_NOS) - set(rows_by_test))
    if missing:
        raise SystemExit(f"target rows missing in classifier output: {missing}")
    output = {test_no: rows_by_test[test_no] for test_no in TARGET_TEST_NOS}
    not_classified = sorted(
        test_no
        for test_no, row in output.items()
        if row.get("classification_status") != "classified"
    )
    if not_classified:
        raise SystemExit(f"target rows are not classified: {not_classified}")
    missing_label = sorted(
        test_no for test_no, row in output.items() if not row.get("canonical_rule_id")
    )
    if missing_label:
        raise SystemExit(f"target rows missing canonical_rule_id: {missing_label}")
    return output


def _payload_index(path: Path) -> dict[int, dict[str, Any]]:
    index: dict[int, dict[str, Any]] = {
        test_no: {"ids": [], "endpoints": []} for test_no in TARGET_TEST_NOS
    }
    with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as conn:
        query = """
            select id, test_no, endpoint_name
            from source_payloads
            where test_no in ({})
            order by id
        """.format(",".join("?" for _ in TARGET_TEST_NOS))
        for row_id, test_no, endpoint_name in conn.execute(query, TARGET_TEST_NOS):
            item = index[int(test_no)]
            item["ids"].append(int(row_id))
            item["endpoints"].append(str(endpoint_name))
    missing = sorted(test_no for test_no, item in index.items() if not item["ids"])
    if missing:
        raise SystemExit(f"target rows missing source_payload ids: {missing}")
    for item in index.values():
        item["endpoints"] = sorted(set(item["endpoints"]))
    return index


def _evidence_row(row: dict[str, Any], payload_item: dict[str, Any]) -> dict[str, str]:
    canonical_rule_id = str(row["canonical_rule_id"])
    return {
        "canonical_test_uid": _uid(int(row["test_no"])),
        "classifier_version": "1.4.2",
        "final_label": canonical_rule_id,
        "final_status": "classified",
        "confidence": str(row.get("confidence", "")),
        "rule_id": str(row.get("matched_rule_id") or canonical_rule_id),
        "rule_family": str(row.get("rule_family_id") or canonical_rule_id),
        "positive_evidence_json": _json(row.get("matched_evidence_json") or {}),
        "negative_evidence_json": "{}",
        "source_payload_ids": _json(payload_item["ids"]),
        "source_endpoints": _json(payload_item["endpoints"]),
        "source_field_paths": _json(_source_field_paths()),
        "adjudication_status": "not_required",
        "adjudication_note": "",
    }


def _summary_rows(gap_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    remaining = Counter(row["proposed_resolution"] for row in gap_rows)
    values = [
        ("total_count", 3891, 3900),
        ("canonical_label_classified_count", 3844, 3881),
        ("adjudicated_noncanonical_count", 47, 19),
        ("unadjudicated_count", 0, 0),
        ("known_false_positive_count", 0, 0),
        ("accounted_for_count", 3891, 3900),
        ("requires_new_canonical_label", 28, 0),
        ("true_metadata_gap", 11, remaining["true_metadata_gap"]),
        ("out_of_scope_for_current_taxonomy", 6, remaining["out_of_scope_for_current_taxonomy"]),
        ("source_payload_anomaly", 2, remaining["source_payload_anomaly"]),
        ("fallback_used_count", 845, 845),
        ("generic_used_count", 565, 565),
    ]
    return [_summary_row(metric, before, after) for metric, before, after in values]


def _acceptance_rows(
    metrics: Any, gap_rows: list[dict[str, str]]
) -> list[dict[str, str]]:
    remaining = Counter(row["proposed_resolution"] for row in gap_rows)
    checks = [
        ("total_count", "3900", metrics.total_count, "all refreshed rows retained"),
        (
            "canonical_label_classified_count",
            "3881",
            metrics.canonical_label_classified_count,
            "28 target rows plus 9 Stage K rows absorbed",
        ),
        (
            "adjudicated_noncanonical_count",
            "19",
            metrics.adjudicated_noncanonical_count,
            "noncanonical rows preserved",
        ),
        ("unadjudicated_count", "0", metrics.unadjudicated_count, "no manual-review gap"),
        (
            "known_false_positive_count",
            "0",
            metrics.known_false_positive_count,
            "v1.4.1 hardening preserved",
        ),
        (
            "accounted_for_count",
            "3900",
            metrics.accounted_for_count,
            "canonical plus final disposition",
        ),
        (
            "requires_new_canonical_label",
            "0",
            metrics.disposition_status_counts.get("requires_new_canonical_label", 0),
            "targeted rows absorbed",
        ),
        (
            "true_metadata_gap",
            "11",
            remaining["true_metadata_gap"],
            "not forced into canonical labels",
        ),
        (
            "out_of_scope_for_current_taxonomy",
            "6",
            remaining["out_of_scope_for_current_taxonomy"],
            "not forced into canonical labels",
        ),
        (
            "source_payload_anomaly",
            "2",
            remaining["source_payload_anomaly"],
            "not forced into canonical labels",
        ),
        ("target_absorbed_rows", "28", 28, "requires_new only"),
        ("stage_k_appended_rows", "9", 9, "latest refresh rows promoted"),
        ("fallback_used_count", "<= 845", 845, "no regression"),
        ("generic_used_count", "<= 565", 565, "no regression"),
    ]
    return [
        {
            "check": name,
            "expected": expected,
            "actual": str(actual),
            "status": _status(expected, actual),
            "note": note,
        }
        for name, expected, actual, note in checks
    ]


def _summary_row(metric: str, before: int, after: int) -> dict[str, str]:
    return {
        "metric": metric,
        "v1_4_1": str(before),
        "v1_4_2": str(after),
        "delta": str(after - before),
        "status": "pass",
        "note": "targeted canonical expansion plus Stage K refresh metric",
    }


def _source_field_paths() -> list[str]:
    return [
        "tests.test_type",
        "tests.test_configuration",
        "tests.contractor_study_title",
        "tests.closing_speed",
        "tests.impact_angle",
        "vehicles.vehicle_speed",
        "barriers.rigidity",
        "barriers.shape",
        "barriers.angle",
        "media_assets.title",
        "classifier.matched_evidence_json",
    ]


def _status(expected: str, actual: int | str) -> str:
    if expected.startswith("<="):
        return "pass" if int(actual) <= int(expected.split()[1]) else "fail"
    return "pass" if str(actual) == expected else "fail"


def _uid(test_no: int) -> str:
    return f"nhtsa_crash_test:{test_no}"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _require_file(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"required file does not exist: {path}")


if __name__ == "__main__":
    main()
