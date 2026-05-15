# 2026-05-07 | Project Closure | CLOSED WITH DOCUMENTED EXCEPTIONS | nhtsa_metadata

## Scope

This closure covers `nhtsa_metadata` only.

The downstream `nhtsa_gui` project is not part of this closure. GUI design,
API/UI exposure, and product interaction work remain separate downstream work.

## Closure Decision

Decision: closed with documented exceptions.

The project is closed because the 2011+ NHTSA crash test metadata-only corpus is
materialized, rebuildable from preserved source payloads, and covered by
project verification. Completion is not defined as `classified_count = 3891`.

The accepted completion frame is:

- `accounted_for_count`, not all-row canonical classification.
- `known_false_positive_count = 0`.
- `unadjudicated_count = 0`.
- schema hard failures are zero.
- every accepted row is covered by traceable canonical classification evidence
  or traceable final noncanonical disposition evidence.

## Final Output DB

Final materialized DB:

```text
D:\vscode\nhtsa_metadata\data\full_2011plus_metadata_filter_ready_2026-05-04.sqlite
```

This SQLite file is an ignored runtime artifact under `data/`; it is not
committed. The committed code, migrations, fixtures, and phase reports define
how to regenerate and validate it.

Read-only DB check:

| Item | Value |
|---|---:|
| DB size | 2,762,768,384 bytes |
| table count | 42 |
| `tests` | 3,900 |
| `vehicles` | 4,705 |
| `source_payloads` | 66,477 |
| `test_classification` | 3,900 |
| `test_filter_summary` | 3,900 |
| `barrier_load_cell_classification` | 1,137 |
| `barrier_load_cell_channel_map` | 0 |

Date scope:

| Check | Result |
|---|---:|
| min `test_date` | 2011-01-03 |
| max `test_date` | 2025-11-19 |
| rows before 2011-01-01 | 0 |
| rows after 2026-05-04 | 0 |

## Accounting Metrics

The original v1.0 readiness gate was established on the 3,891-row Stage D
corpus. Stage K then refreshed the corpus with 9 additional in-scope tests and
promoted the tracked classification and lineage fixtures to 3,900 rows.

Final tracked acceptance metrics from
`tests/fixtures/classification/classification_summary_v1_4_2.csv`:

| Metric | Value |
|---|---:|
| `total_count` | 3,900 |
| `canonical_label_classified_count` | 3,881 |
| `adjudicated_noncanonical_count` | 19 |
| `unadjudicated_count` | 0 |
| `known_false_positive_count` | 0 |
| `accounted_for_count` | 3,900 |
| `requires_new_canonical_label` | 0 |
| `true_metadata_gap` | 11 |
| `out_of_scope_for_current_taxonomy` | 6 |
| `source_payload_anomaly` | 2 |

Final tracked lineage metrics from
`tests/fixtures/classification/classification_lineage_audit_v1_6.csv`:

| Metric | Value |
|---|---:|
| data rows | 3,900 |
| `lineage_status = complete` | 3,900 |
| `final_status = classified` | 3,881 |
| `final_status = true_metadata_gap` | 11 |
| `final_status = out_of_scope_for_current_taxonomy` | 6 |
| `final_status = source_payload_anomaly` | 2 |

The 19 noncanonical rows are final dispositions and are not forced into
canonical labels.

## DB Projection Caveat

The materialized filter-ready DB contains a simplified `test_classification`
projection. Its current DB-level status counts are:

| Status | Count |
|---|---:|
| `classification_status = classified` | 3,891 |
| `classification_status = needs_review` | 9 |
| `disposition_status = manual_review_required` | 3,900 |

This DB projection is not the final acceptance source for v1.4.2/v1.6
accounting. Final acceptance is grounded in the tracked classification summary
and lineage audit fixtures promoted by Stage K. This distinction is documented
so the project is not incorrectly described as an all-row canonical classifier.

## Stage Closeout Evidence

| Stage | Evidence |
|---|---|
| Stage H | `docs/phase_reports/stage_h_classification_disposition_schema_result.md` |
| Stage I | `docs/phase_reports/stage_i_v1_4_2_targeted_canonical_expansion_result.md` |
| Stage J | `docs/phase_reports/stage_j_schema_v1_6_evidence_model_result.md` |
| Stage K | `docs/phase_reports/stage_k_incremental_refresh_2011plus_2026-05-03.md` |
| Stage K vehicle fields | `docs/phase_reports/stage_k_vehicle_filter_promotion_result.md` |
| Stage L | `docs/phase_reports/stage_l_barrier_load_cell_db_integration_result.md` |
| Stage M | `docs/phase_reports/stage_m_filter_ready_db_materialization_result.md` |
| v1.0 release readiness | `docs/phase_reports/v1_0_release_readiness_report.md` |

## nhtsa_gui Boundary

`nhtsa_gui` is a downstream consumer of this project output. It is intentionally
excluded from this closure because GUI design and product interaction work still
need separate completion criteria.

This project closure does not require:

- GUI design completion.
- GUI filter UI completion.
- GUI API/UI exposure for every mirrored metadata field.
- GUI DB import redesign.
- push.
- merge to `main`.

## Validation

Final closure validation commands:

| Command | Result |
|---|---|
| `git status -sb` | passed; clean before report creation, then only this report was untracked |
| `git log --oneline -8` | passed |
| read-only SQLite DB checks | passed |
| `pytest -q` | passed, `135 passed, 4 warnings` |
| `ruff check .` | passed |
| `mypy src\nhtsa_metadata` | passed, `52 source files` |
| `powershell -ExecutionPolicy Bypass -File scripts\verify.ps1` | passed |
| `powershell -ExecutionPolicy Bypass -File .harness\run.ps1` | passed |

## Remaining Risks

- The final SQLite DB is ignored under `data/`; consumers must use the generated
  artifact path or regenerate it with the committed materialization command.
- The simplified DB projection status should not be used to claim all 3,900 rows
  are canonical-label classified.
- `nhtsa_gui` still needs separate design and product readiness work.

## Hard Constraint Compliance

- No new worktree was created.
- No repository folder was created or cloned.
- No live NHTSA API call was made during closure.
- No production or raw source payload data was rewritten.
- No push was performed.
- No merge to `main` was performed.

## Final Status

`nhtsa_metadata` is closed with documented exceptions as a metadata-only corpus
DB project. Downstream GUI productization remains separate work.
