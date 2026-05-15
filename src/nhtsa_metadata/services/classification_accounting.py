from __future__ import annotations

import csv
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

CLASSIFICATION_STATUSES = frozenset(
    {
        "classified",
        "unclassified",
        "ambiguous",
        "generic_mode_only",
        "out_of_scope",
    }
)

DISPOSITION_STATUSES = frozenset(
    {
        "canonical_label_assigned",
        "requires_new_canonical_label",
        "true_metadata_gap",
        "out_of_scope_for_current_taxonomy",
        "source_payload_anomaly",
        "manual_review_required",
        "adjudicated_no_action",
    }
)

ADJUDICATION_STATUSES = frozenset(
    {
        "not_required",
        "pending",
        "accepted",
        "rejected",
        "superseded",
        "adjudicated",
    }
)

NONCANONICAL_FINAL_DISPOSITIONS = frozenset(
    {
        "requires_new_canonical_label",
        "true_metadata_gap",
        "out_of_scope_for_current_taxonomy",
        "source_payload_anomaly",
        "adjudicated_no_action",
    }
)


@dataclass(frozen=True)
class ClassificationAccountingMetrics:
    total_count: int
    accounted_for_count: int
    canonical_label_classified_count: int
    adjudicated_noncanonical_count: int
    unadjudicated_count: int
    known_false_positive_count: int
    classification_status_counts: dict[str, int]
    disposition_status_counts: dict[str, int]


def read_classification_fixture(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_classification_fixture(
    path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, object]]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def classification_status_for_evidence(row: Mapping[str, str]) -> str:
    final_status = row.get("final_status", "")
    if final_status == "classified":
        return "classified"
    if final_status == "out_of_scope_for_current_taxonomy":
        return "out_of_scope"
    return "unclassified"


def disposition_status_for_evidence(row: Mapping[str, str]) -> str:
    final_status = row.get("final_status", "")
    if final_status == "classified":
        return "canonical_label_assigned"
    if final_status in DISPOSITION_STATUSES:
        return final_status
    return "manual_review_required"


def compute_accounting_metrics(
    evidence_rows: Sequence[Mapping[str, str]], *, known_false_positive_count: int
) -> ClassificationAccountingMetrics:
    classification_counts = Counter(
        classification_status_for_evidence(row) for row in evidence_rows
    )
    disposition_counts = Counter(disposition_status_for_evidence(row) for row in evidence_rows)
    canonical_count = disposition_counts["canonical_label_assigned"]
    adjudicated_noncanonical_count = sum(
        disposition_counts[status] for status in NONCANONICAL_FINAL_DISPOSITIONS
    )
    unadjudicated_count = disposition_counts["manual_review_required"]
    return ClassificationAccountingMetrics(
        total_count=len(evidence_rows),
        accounted_for_count=canonical_count + adjudicated_noncanonical_count,
        canonical_label_classified_count=canonical_count,
        adjudicated_noncanonical_count=adjudicated_noncanonical_count,
        unadjudicated_count=unadjudicated_count,
        known_false_positive_count=known_false_positive_count,
        classification_status_counts=dict(sorted(classification_counts.items())),
        disposition_status_counts=dict(sorted(disposition_counts.items())),
    )


def gap_resolution_counts(gap_rows: Sequence[Mapping[str, str]]) -> dict[str, int]:
    return dict(sorted(Counter(row["proposed_resolution"] for row in gap_rows).items()))
