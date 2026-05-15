# 2026-05-03 | Stage H | PLANNED | Classification Disposition Schema Plan

## 1. Purpose

Stage H defines the operating schema needed to separate classifier status from final disposition status.

The goal is to make `accounted_for_count = 3891` measurable without pretending every accounted row has a canonical label.

## 2. Why classification_status and disposition_status must be separated

`classification_status` describes what the classifier did.

`disposition_status` describes how the project accounts for the row after classifier output and adjudication.

Without this split:

- a true metadata gap may be misreported as an unclassified failure;
- a taxonomy out-of-scope row may be forced into a canonical label;
- a source payload anomaly may hide as classifier failure;
- `classified_count` can be confused with `accounted_for_count`.

## 3. Proposed classification_status enum

Minimum proposal:

- `classified`
- `unclassified`
- `ambiguous`
- `generic_mode_only`
- `out_of_scope`

Interpretation:

- `classified`: a canonical label was assigned by rule or accepted adjudication.
- `unclassified`: no acceptable candidate was found.
- `ambiguous`: multiple candidates remain unresolved.
- `generic_mode_only`: only a generic physical mode is supported; no protocol-level label is accepted.
- `out_of_scope`: row is outside the current classifier taxonomy.

## 4. Proposed disposition_status enum

Minimum proposal:

- `canonical_label_assigned`
- `requires_new_canonical_label`
- `true_metadata_gap`
- `out_of_scope_for_current_taxonomy`
- `source_payload_anomaly`
- `manual_review_required`
- `adjudicated_no_action`

Interpretation:

- `canonical_label_assigned`: final canonical label is accepted.
- `requires_new_canonical_label`: source evidence supports a real class, but taxonomy lacks the label.
- `true_metadata_gap`: source payload lacks enough metadata for classification.
- `out_of_scope_for_current_taxonomy`: row is valid but outside current taxonomy boundaries.
- `source_payload_anomaly`: source data is internally inconsistent or anomalous.
- `manual_review_required`: no final disposition yet.
- `adjudicated_no_action`: final review accepted that no schema/rule change is needed.

## 5. Proposed adjudication_status enum if useful

Optional proposal:

- `not_required`
- `pending`
- `accepted`
- `rejected`
- `superseded`

Use this only if audit history needs to distinguish current final disposition from earlier review attempts.

## 6. Proposed classification_adjudication table

Purpose: preserve final human or rule-owner disposition decisions for rows that are not straightforward canonical classifications.

Suggested fields:

- `id`
- `test_id`
- `test_no`
- `classification_run_id`
- `classification_status`
- `disposition_status`
- `adjudication_status`
- `adjudication_reason`
- `expected_domain`
- `expected_rule_if_known`
- `recommended_action`
- `reviewer`
- `reviewed_at`
- `source_endpoint_name`
- `source_section_name`
- `source_row_path`
- `source_row_hash`
- `created_at`

## 7. Proposed classification_evidence table semantics

Purpose: preserve evidence behind classifier output and final disposition.

Required semantics:

- winning match evidence and candidate evidence are separate;
- no-candidate rows record that candidate set was empty;
- false-positive rows preserve the losing expected candidate when known;
- evidence points back to source payload, endpoint, row path, and normalized feature extract;
- evidence can be regenerated from raw/provenance inputs.

## 8. Proposed test_classification table updates

Potential updates:

- add or clarify `classification_status`;
- add `disposition_status`;
- add `canonical_rule_id`;
- add `rule_family_id`;
- add `specificity_level`;
- add `confidence`;
- add `classification_run_id`;
- add timestamps or rebuild metadata if not already present.

Do not overload existing `classification_status` to mean both classifier result and final accounting state.

## 9. Proposed test_classification_candidates table

Purpose: store ranked candidate rules for each row and run.

Suggested fields:

- `id`
- `classification_run_id`
- `test_id`
- `test_no`
- `rank`
- `rule_id`
- `canonical_rule_id`
- `rule_family_id`
- `program_domain`
- `specificity_level`
- `priority`
- `score`
- `matched_evidence_json`
- `fallback_used`
- `alias_used`
- `created_at`

## 10. 47-row triage fixture or seed strategy

Create a bounded fixture or seed surface for the original 47 rows:

- 28 `requires_new_canonical_label`
- 11 `true_metadata_gap`
- 6 `out_of_scope_for_current_taxonomy`
- 2 `source_payload_anomaly`

Fixture requirements:

- preserve original `test_no`;
- preserve v1.4 feature summary or row-level evidence;
- preserve source endpoint and row hash where available;
- separate current disposition from future v1.4.2 canonical expansion;
- avoid using live API calls in default tests.

## 11. Acceptance metrics

Stage H is accepted when reports can compute:

- `total_count = 3891`
- `accounted_for_count = 3891`
- `canonical_label_classified_count`
- `adjudicated_noncanonical_count`
- `unadjudicated_count = 0`
- `known_false_positive_count = 0`
- classification/disposition split is visible in reports

## 12. Reporting implications

Reports must show:

- classifier output count;
- canonical classification count;
- final noncanonical disposition count;
- manual review count;
- known false-positive count;
- before/after v1.4.2 metric framing;
- remaining exceptions by bounded disposition status.

## 13. CLI/reporting implications

CLI reports should add or preserve commands that can emit:

- classification run summary;
- false-positive regression summary;
- disposition summary;
- row-level adjudication export;
- evidence lineage audit.

Default CLI, `pytest`, `scripts/verify.ps1`, and `.harness/run.ps1` must not call live NHTSA APIs.

## 14. Done criteria

Stage H is done when:

- enum semantics are documented and implemented if approved;
- adjudication and evidence table semantics are accepted;
- the 47-row triage fixture or seed strategy is reproducible;
- `accounted_for_count` can be computed separately from `canonical_label_classified_count`;
- reports distinguish unclassified failure from final noncanonical disposition.

## 15. Non-goals

- Do not add broad production dependencies.
- Do not redesign unrelated schema areas.
- Do not implement v1.4.2 targeted labels.
- Do not perform live source collection.
- Do not force source gaps into canonical labels.

## 16. Risks

- enum names can become too broad and hide real classifier failures;
- storing only final evidence can lose candidate ranking auditability;
- fixture data can drift from the original v1.4 failure package if copied manually;
- report users may still confuse `accounted_for_count` with `classified_count`.

## 17. Rollback points

- rollback schema migration if enum split breaks existing read models;
- rollback adjudication fixture if source row hashes cannot be verified;
- rollback CLI/report changes if default verification starts requiring live API access.
