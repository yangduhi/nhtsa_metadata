# 2026-05-03 | Stage H | COMPLETE | Classification Disposition Schema Result

## Purpose

Stage H implements the baseline split between classifier output status and final
project accounting disposition. This makes `accounted_for_count = 3891`
measurable without treating every accounted row as a canonical label.

## Branch and workspace

- Branch: `codex/stage-h-to-v1-completion`
- Workspace: `D:\vscode\nhtsa_metadata`
- Registered worktrees: one canonical worktree only.
- New worktree created: no.

## Implemented schema surface

Updated `test_classification` with final accounting fields:

- `disposition_status`
- `canonical_label`
- `canonical_rule_id`
- `rule_family_id`
- `specificity_level`
- `confidence`
- `classification_run_id`
- `evidence_summary_json`

Added ORM and Alembic-managed tables:

- `classification_adjudication`
- `test_classification_candidates`

The Alembic migration is:

- `alembic/versions/0003_classification_disposition_schema.py`

This does not rename or alter the standalone Stage F SQL artifact
`migrations/0003_schema_contract_v1_5.sql`.

## Status vocabulary

`classification_status` is limited to classifier outcome semantics:

- `classified`
- `unclassified`
- `ambiguous`
- `generic_mode_only`
- `out_of_scope`

`disposition_status` is limited to final accounting semantics:

- `canonical_label_assigned`
- `requires_new_canonical_label`
- `true_metadata_gap`
- `out_of_scope_for_current_taxonomy`
- `source_payload_anomaly`
- `manual_review_required`
- `adjudicated_no_action`

## 47-row triage preservation

The original v1.4/v1.4.1 triage remains represented from
`tests/fixtures/classification/classification_gap_triage_v1_4_1.csv`:

- `requires_new_canonical_label = 28`
- `true_metadata_gap = 11`
- `out_of_scope_for_current_taxonomy = 6`
- `source_payload_anomaly = 2`

These remain final disposition categories, not forced canonical labels.

## Stage H metrics

Using `classification_evidence_v1_4_1.csv`:

- `total_count = 3891`
- `canonical_label_classified_count = 3844`
- `adjudicated_noncanonical_count = 47`
- `unadjudicated_count = 0`
- `known_false_positive_count = 0`
- `accounted_for_count = 3891`

Classification status counts:

- `classified = 3844`
- `out_of_scope = 6`
- `unclassified = 41`

Disposition status counts:

- `canonical_label_assigned = 3844`
- `requires_new_canonical_label = 28`
- `true_metadata_gap = 11`
- `out_of_scope_for_current_taxonomy = 6`
- `source_payload_anomaly = 2`

## Tests added or updated

- `tests/test_classification_accounting.py`
- `tests/test_db_migrations.py`

## Validation

Stage H validation passed:

- `pytest -q`: passed, `123 passed, 2 warnings`.
- `ruff check .`: passed.
- `mypy src\nhtsa_metadata`: passed, `49 source files`.
- `powershell -ExecutionPolicy Bypass -File scripts\verify.ps1`: passed.
- `powershell -ExecutionPolicy Bypass -File .harness\run.ps1`: passed.

## Non-goals honored

- Stage I v1.4.2 targeted labels were not implemented in Stage H.
- Stage J evidence-lineage operating model was not implemented in Stage H.
- No live NHTSA API calls were made.
- No raw source payloads were modified.
- No production data was rewritten.
