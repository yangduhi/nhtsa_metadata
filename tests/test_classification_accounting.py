from pathlib import Path

from nhtsa_metadata.services.classification_accounting import (
    CLASSIFICATION_STATUSES,
    DISPOSITION_STATUSES,
    compute_accounting_metrics,
    gap_resolution_counts,
    read_classification_fixture,
)

FIXTURE_DIR = Path("tests/fixtures/classification")


def test_stage_h_status_vocabularies_are_separate() -> None:
    assert {
        "classified",
        "unclassified",
        "ambiguous",
        "generic_mode_only",
        "out_of_scope",
    } <= CLASSIFICATION_STATUSES
    assert {
        "canonical_label_assigned",
        "requires_new_canonical_label",
        "true_metadata_gap",
        "out_of_scope_for_current_taxonomy",
        "source_payload_anomaly",
        "manual_review_required",
        "adjudicated_no_action",
    } <= DISPOSITION_STATUSES
    assert "requires_new_canonical_label" not in CLASSIFICATION_STATUSES
    assert "classified" not in DISPOSITION_STATUSES


def test_stage_h_v1_4_1_accounting_metrics_keep_classification_and_disposition_split() -> None:
    evidence_rows = read_classification_fixture(
        FIXTURE_DIR / "classification_evidence_v1_4_1.csv"
    )
    metrics = compute_accounting_metrics(evidence_rows, known_false_positive_count=0)

    assert metrics.total_count == 3891
    assert metrics.canonical_label_classified_count == 3844
    assert metrics.adjudicated_noncanonical_count == 47
    assert metrics.unadjudicated_count == 0
    assert metrics.known_false_positive_count == 0
    assert metrics.accounted_for_count == 3891
    assert metrics.classification_status_counts == {
        "classified": 3844,
        "out_of_scope": 6,
        "unclassified": 41,
    }
    assert metrics.disposition_status_counts == {
        "canonical_label_assigned": 3844,
        "out_of_scope_for_current_taxonomy": 6,
        "requires_new_canonical_label": 28,
        "source_payload_anomaly": 2,
        "true_metadata_gap": 11,
    }


def test_stage_h_original_47_triage_is_representable() -> None:
    gap_rows = read_classification_fixture(FIXTURE_DIR / "classification_gap_triage_v1_4_1.csv")

    assert gap_resolution_counts(gap_rows) == {
        "out_of_scope_for_current_taxonomy": 6,
        "requires_new_canonical_label": 28,
        "source_payload_anomaly": 2,
        "true_metadata_gap": 11,
    }
