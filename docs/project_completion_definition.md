# 2026-05-03 | Project Completion | PLANNED | NHTSA_metadata 2011+ v1.0 Completion Definition

## 1. Executive summary

The v1.0 completion point is not `classified_count = 3891`.

The project is complete when every in-scope 2011+ metadata row is accounted for by either:

1. a canonical test type classification with traceable source evidence, normalized features, candidate rule evidence, and final rule decision; or
2. a final noncanonical disposition with traceable adjudication evidence.

The operating target is:

- `total_count = 3891`
- `accounted_for_count = 3891`
- `known_false_positive_count = 0`
- `unadjudicated_count = 0`
- schema and endpoint hard failures remain zero
- classification evidence lineage is explicit and reproducible

This document freezes the completion definition for planning. It does not declare the project complete.

## 2. Current project state

Confirmed in the current repository snapshot:

- Stage D 2011+ full-corpus evidence package exists under `docs/phase_reports/v1_4_full_corpus_failure_package_2026-05-02/`.
- v1.4 full-corpus classification report records `total_count = 3891`, `classified_count = 3844`, `unclassified_count = 47`, and `known_false_positive_count = 26`.
- Full-scale endpoint completeness records `expected_tests = 3891`, `collected_tests = 3891`, `missing_tests = 0`, `source_payload_count = 66318`, and `source_payload_observations_count = 66318`.
- Full-scale schema audit records `schema_contract_hard_failures = 0`, `endpoint_matrix_hard_failures = 0`, and `source_payload_immutability = pass`.
- The v1.4 failure manifest preserves 47 unclassified rows plus 26 known false-positive rows with row-level evidence.

Project state provided by the current goal prompt and treated as planning input:

- v1.4.1 reduced `known_false_positive_count` to 0.
- the original 47 unclassified rows were triaged or adjudicated.
- the original 47-row triage is:
  - `requires_new_canonical_label = 28`
  - `true_metadata_gap = 11`
  - `out_of_scope_for_current_taxonomy = 6`
  - `source_payload_anomaly = 2`
- schema v1.5 is an acceptable integration baseline with documented exceptions, but it is not the final operating evidence/disposition schema.

## 3. Definition of complete

The NHTSA_metadata v1.0 2011+ metadata-only project is complete when all of the following are true:

- every canonical/read-model row has `test_date >= 2011-01-01`;
- every in-scope row is represented in the completion accounting set;
- every in-scope row has either a canonical classification or a final noncanonical disposition;
- every canonical classification has source payload, normalized feature, candidate rule, and final decision lineage;
- every final noncanonical disposition has adjudication evidence and an explicit disposition reason;
- `accounted_for_count = total_count = 3891`;
- `known_false_positive_count = 0`;
- `unadjudicated_count = 0`;
- schema contract hard failures and endpoint matrix hard failures are zero;
- source payload immutability passes;
- migration numbering is reconciled with no conflicting Alembic heads;
- remaining exceptions are documented, bounded, and non-blocking.

## 4. Definition of not complete

The project is not complete if any of the following are true:

- completion is defined only as `classified_count = 3891`;
- any in-scope row is neither canonically classified nor finally disposed;
- any known false-positive remains accepted as a valid classifier result;
- any row remains in manual review without a final disposition;
- schema v1.5 is treated as the final operating evidence model without disposition lineage;
- classifier v1.4.1 is treated as all-row canonical classifier acceptance;
- true metadata gaps, taxonomy out-of-scope rows, or source payload anomalies are forced into canonical labels;
- validation commands are listed but not runnable or not actually run before merge readiness;
- production data, migrations, or classifier logic are changed before the completion definition is frozen.

## 5. Completion metrics

Core acceptance metrics:

| metric | required value | meaning |
|---|---:|---|
| `total_count` | 3891 | in-scope 2011+ metadata-only rows |
| `accounted_for_count` | 3891 | canonical classifications plus final noncanonical dispositions |
| `known_false_positive_count` | 0 | accepted classifier results known to be wrong |
| `unadjudicated_count` | 0 | rows without final classification or final disposition |
| `schema_contract_hard_failure` | 0 | blocking schema contract failures |
| `endpoint_matrix_hard_failure` | 0 | blocking endpoint matrix failures |
| `source_payload_immutability` | pass | raw/provenance payloads remain immutable |
| `migration_conflict` | 0 | no conflicting migration heads or numbering collision |

Recommended metric framing before v1.4.2:

| metric | value |
|---|---:|
| `total_count` | 3891 |
| `canonical_label_classified_count` | 3844 |
| `adjudicated_noncanonical_count` | 47 |
| `unadjudicated_count` | 0 |
| `known_false_positive_count` | 0 |
| `accounted_for_count` | 3891 |

Recommended metric framing after v1.4.2 targeted canonical expansion:

| metric | value |
|---|---:|
| `total_count` | 3891 |
| `canonical_label_classified_count` | 3872 |
| `adjudicated_noncanonical_count` | 19 |
| `unadjudicated_count` | 0 |
| `known_false_positive_count` | 0 |
| `accounted_for_count` | 3891 |

`canonical_label_classified_count` must remain separate from `accounted_for_count`.

## 6. Non-goals / anti-goals

- Do not define v1.0 completion as `classified_count = 3891`.
- Do not force all rows into canonical labels.
- Do not modify production data under `data/`.
- Do not perform live NHTSA API calls for this completion-definition work.
- Do not change classifier logic in this goal.
- Do not change migrations in this goal.
- Do not merge, push, or commit as part of this goal.
- Do not treat schema v1.5 as the final operating evidence/disposition schema.
- Do not treat v1.4.1 as all-row canonical classifier acceptance.

## 7. Required evidence lineage

Every final outcome must be traceable through this chain:

`source_payload -> normalized_feature -> candidate_rule -> final_classification_or_final_disposition`

Required lineage properties:

- source endpoint, section, row path, and row hash are preserved where applicable;
- raw payload and source observation remain rebuildable provenance inputs;
- normalized features record the extracted signals used for matching;
- candidate rules preserve rule id, canonical rule id, score, specificity, matched evidence, and fallback or alias usage;
- the final classification stores the selected rule and why it won;
- the final disposition stores the adjudication reason and evidence when no canonical label is assigned.

## 8. Classification vs disposition model

Canonical classification answers: "Which canonical test type label applies?"

Final disposition answers: "If no canonical label is assigned, why is the row still accounted for?"

These are separate because a row can be fully accounted for without being assigned a canonical label. Examples include true metadata gaps, taxonomy out-of-scope rows, and source payload anomalies.

## 9. Acceptance gates

Before implementation readiness:

- completion definition is approved;
- Stage G/H/I/J plans exist and are reviewable;
- `classification_status` and `disposition_status` are defined separately;
- evidence lineage requirements are explicit;
- no production data, classifier logic, or migrations were changed by the definition work.

Before merge readiness:

- schema contract validation passes;
- endpoint matrix validation passes;
- false-positive regression checks pass;
- fallback/generic regression checks pass;
- migration heads are reconciled;
- all remaining exceptions are documented and bounded.

## 10. Stop rules

Stop the definition goal when:

- this document exists and defines complete and not complete;
- Stage G/H/I/J plan files exist;
- acceptance metrics are measurable;
- anti-goals are explicit;
- validation commands are listed;
- documentation diff is reviewable;
- no implementation changes are required;
- no production data was modified;
- no branch merge, push, or commit was performed.

## 11. Validation commands

Lightweight documentation checks:

```powershell
git status
git diff --stat
git diff -- docs/project_completion_definition.md docs/phase_reports/
```

Repository checks before implementation or merge readiness, if available and appropriate:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1
pytest -q
ruff check .
mypy .
powershell -ExecutionPolicy Bypass -File .harness/run.ps1
```

Do not report a command as passed unless it actually ran and passed.

## 12. Merge readiness criteria

Merge readiness requires:

- review approval for this completion definition and the Stage G/H/I/J plans;
- clean documentation diff for this goal;
- no unrelated dirty changes included in merge scope;
- no live API dependency in default verification;
- no production data mutation;
- no classifier or migration change hidden in documentation work;
- passing repository checks or explicit owner-approved skip reasons;
- updated phase report evidence for the implementation stage being merged.

## 13. Rollback points

- Before Stage G: revert only the documentation files created for the completion definition if the framing is rejected.
- During Stage G: rollback to the pre-integration branch tip if schema v1.5 and classifier v1.4.1 reconciliation creates migration or semantic conflicts.
- During Stage H: rollback schema changes if classification and disposition states are not separable without breaking read-model contracts.
- During Stage I: rollback v1.4.2 targeted rules if false-positive or fallback/generic regressions appear.
- During Stage J: rollback schema v1.6 evidence model if lineage tables cannot be rebuilt deterministically from raw/provenance inputs.

## 14. Remaining risks

- v1.4.1 and schema v1.5 evidence was not fully present in the current repository snapshot; this document treats the prompt-provided state as planning input until Stage G verifies the artifacts.
- The expected Stage D worktree path was not present at authoring time; Stage G should confirm the intended starting branch and worktree before implementation.
- Existing unrelated dirty changes in the current repository must not be mixed into Stage G implementation scope.
- A final disposition schema can become too permissive if it lets real classifier gaps hide as adjudicated exceptions.
- New canonical labels in v1.4.2 may introduce false positives unless regression checks preserve v1.4.1 hardening.

## 15. Glossary

- `total_count`: count of in-scope 2011+ metadata-only rows subject to completion accounting.
- `accounted_for_count`: count of rows with either final canonical classification or final noncanonical disposition.
- `canonical_label_classified_count`: count of rows assigned a canonical test type label.
- `adjudicated_noncanonical_count`: count of rows with final disposition but no canonical label assignment.
- `unadjudicated_count`: count of rows without final canonical classification or final disposition.
- `known_false_positive_count`: count of classifier outputs known to be wrong by explicit regression checks.
- `schema_contract_hard_failure`: blocking schema contract violation count.
- `endpoint_matrix_hard_failure`: blocking endpoint matrix violation count.
- `classification_status`: classifier outcome state, separate from final disposition.
- `disposition_status`: accounting/adjudication state for canonical and noncanonical outcomes.
- `classification_evidence_lineage`: source payload, normalized feature, candidate rule, and final decision trace.
- `source_payload`: immutable raw/provenance payload captured from a source endpoint.
- `normalized_feature`: extracted and normalized matching signal derived from source payloads and canonical rows.
- `candidate_rule`: rule considered by the classifier with score, matched evidence, and rule metadata.
- `final_classification`: selected canonical label and rule decision.
- `final_disposition`: final noncanonical accounting result with adjudication evidence.
