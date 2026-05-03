from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from nhtsa_metadata.services.classification_accounting import (
    disposition_status_for_evidence,
)


@dataclass(frozen=True)
class ClassificationLineageMetrics:
    total_count: int
    source_payload_linked_count: int
    normalized_feature_linked_count: int
    candidate_or_disposition_linked_count: int
    final_decision_linked_count: int
    complete_lineage_count: int
    missing_lineage_count: int


LINEAGE_COLUMNS = [
    "canonical_test_uid",
    "test_no",
    "classifier_version",
    "source_payload_linked",
    "normalized_feature_linked",
    "candidate_or_disposition_linked",
    "final_decision_linked",
    "lineage_status",
    "final_status",
    "final_label",
    "disposition_status",
]


def build_lineage_audit_rows(
    evidence_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    rows = []
    for row in evidence_rows:
        source_linked = _has_json_items(row.get("source_payload_ids", ""))
        normalized_linked = bool(row.get("positive_evidence_json"))
        candidate_or_disposition_linked = bool(row.get("rule_id")) or bool(
            row.get("adjudication_note")
        )
        final_decision_linked = bool(row.get("final_status")) and (
            bool(row.get("final_label")) or bool(row.get("adjudication_status"))
        )
        complete = (
            source_linked
            and normalized_linked
            and candidate_or_disposition_linked
            and final_decision_linked
        )
        rows.append(
            {
                "canonical_test_uid": row["canonical_test_uid"],
                "test_no": _test_no(row["canonical_test_uid"]),
                "classifier_version": row["classifier_version"],
                "source_payload_linked": str(source_linked).lower(),
                "normalized_feature_linked": str(normalized_linked).lower(),
                "candidate_or_disposition_linked": str(
                    candidate_or_disposition_linked
                ).lower(),
                "final_decision_linked": str(final_decision_linked).lower(),
                "lineage_status": "complete" if complete else "incomplete",
                "final_status": row["final_status"],
                "final_label": row.get("final_label", ""),
                "disposition_status": disposition_status_for_evidence(row),
            }
        )
    return rows


def compute_lineage_metrics(
    audit_rows: Sequence[Mapping[str, str]],
) -> ClassificationLineageMetrics:
    total = len(audit_rows)
    source = _true_count(audit_rows, "source_payload_linked")
    feature = _true_count(audit_rows, "normalized_feature_linked")
    candidate = _true_count(audit_rows, "candidate_or_disposition_linked")
    final = _true_count(audit_rows, "final_decision_linked")
    complete = sum(1 for row in audit_rows if row["lineage_status"] == "complete")
    return ClassificationLineageMetrics(
        total_count=total,
        source_payload_linked_count=source,
        normalized_feature_linked_count=feature,
        candidate_or_disposition_linked_count=candidate,
        final_decision_linked_count=final,
        complete_lineage_count=complete,
        missing_lineage_count=total - complete,
    )


def read_lineage_audit(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_lineage_audit(path: Path, rows: Sequence[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LINEAGE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _has_json_items(value: str) -> bool:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return False
    return isinstance(parsed, list) and len(parsed) > 0


def _test_no(canonical_test_uid: str) -> str:
    return canonical_test_uid.rsplit(":", maxsplit=1)[-1]


def _true_count(rows: Sequence[Mapping[str, str]], field: str) -> int:
    return sum(1 for row in rows if row[field] == "true")
