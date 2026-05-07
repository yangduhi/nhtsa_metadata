# Baseline Report

## Date

2026-05-07

## Repository State

- Repository: `D:\vscode\nhtsa_metadata`
- Branch before refactoring branch creation:
  `codex/stage-h-to-v1-completion`
- Refactoring branch:
  `codex/refactor-post-delivery-hardening`
- Baseline commit:
  `9372b5c05fbc38fe4d63eb06f48a2b6768003a47`
- Baseline status: clean before refactoring branch creation.
- Registered worktrees: one, `D:/vscode/nhtsa_metadata`.

## Scope

This baseline covers `nhtsa_metadata` only. `nhtsa_gui` remains downstream
productization and design work and is not a refactoring blocker for this
project.

## Baseline Commands

Baseline state was captured with read-only inspection and the normal local
verification commands:

```powershell
git status -sb
git branch --show-current
git log --oneline -8
git worktree list --porcelain
Get-FileHash -Algorithm SHA256 data\full_2011plus_metadata_filter_ready_2026-05-04.sqlite
pytest -q
ruff check .
mypy src\nhtsa_metadata
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
powershell -ExecutionPolicy Bypass -File .harness\run.ps1
```

## Final Output Data

Final materialized DB:

```text
D:\vscode\nhtsa_metadata\data\full_2011plus_metadata_filter_ready_2026-05-04.sqlite
```

The DB file is ignored under `data/` and is not committed.

## Output DB Baseline

| Metric | Value |
|---|---:|
| file size bytes | 2,762,768,384 |
| SHA-256 | `366BDFE3AC9F1121C06D138EF096B49AFF4AA0D050485E6061CDF9DACC3CA27D` |
| table count | 42 |
| `tests` | 3,900 |
| `vehicles` | 4,705 |
| `source_payloads` | 66,477 |
| `source_payload_observations` | 66,477 |
| `source_payload_sections` | 101,577 |
| `media_assets` | 290,845 |
| `instrumentation_channels` | 471,566 |
| `injury_metrics` | 39,431 |
| `restraints` | 12,567 |
| `deformation_measurements` | 47,050 |
| `canonical_row_sources` | 1,382,222 |
| `test_classification` | 3,900 |
| `test_filter_summary` | 3,900 |
| `barrier_load_cell_classification` | 1,137 |
| `barrier_load_cell_channel_map` | 0 |

## Scope Checks

| Check | Value |
|---|---:|
| min `test_date` | 2011-01-03 |
| max `test_date` | 2025-11-19 |
| rows before 2011-01-01 | 0 |
| rows after 2026-05-04 | 0 |
| duplicate `tests.test_no` groups | 0 |
| null `tests.test_no` | 0 |
| null `vehicles.test_id` | 0 |
| null `source_payloads.test_no` | 0 |
| null `test_filter_summary.test_no` | 0 |

## Key Output Columns

Baseline `tests` columns:

```text
id, test_no, test_reference_no, test_type, test_date_raw, test_date,
test_date_parse_status, test_performer, contractor_study_title,
test_configuration, test_configuration_key, impact_angle_raw, impact_angle,
offset_distance_raw, offset_distance, closing_speed_raw, closing_speed,
source_payload_id, source_endpoint_name, source_section_name, source_row_path,
source_row_hash, raw_row_json, extra_json, created_at, updated_at
```

Baseline `vehicles` columns:

```text
id, test_id, test_no, source_vehicle_no, make, model, model_year, engine_type,
vehicle_speed_raw, vehicle_speed, vehicle_test_weight_raw, vehicle_test_weight,
source_payload_id, source_endpoint_name, source_section_name, source_row_path,
source_row_hash, raw_row_json, extra_json, created_at, updated_at, body_type,
curb_weight_raw, curb_weight, vehicle_length_raw, vehicle_length,
vehicle_width_raw, vehicle_width, wheelbase_raw, wheelbase,
vax_crush_distance_raw, vax_crush_distance
```

## Completion Metrics

Tracked acceptance metrics from
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

Tracked lineage audit:

- rows: 3,900
- `lineage_status = complete`: 3,900

## Baseline Verification

Already passed before this refactoring work started:

- `pytest -q`: passed, `135 passed, 4 warnings`
- `ruff check .`: passed
- `mypy src\nhtsa_metadata`: passed, `52 source files`
- `powershell -ExecutionPolicy Bypass -File scripts\verify.ps1`: passed
- `powershell -ExecutionPolicy Bypass -File .harness\run.ps1`: passed

The existing `TestFilterSummary` pytest collection warnings are known
non-blocking warnings and are not introduced by this refactoring.

## Baseline Notes

- The DB-level `test_classification` projection is not the final acceptance
  source for all accounting semantics. Final accounting is grounded in tracked
  classification summary and lineage audit fixtures.
- Refactoring must not change the output DB schema, row counts, column names, or
  tracked acceptance metrics unless a separate documented migration task is
  approved.
