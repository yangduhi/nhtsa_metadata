# Validation Report

## Purpose

This report records validation for the post-delivery refactoring pass. The
refactoring is successful only if existing behavior and accepted output metrics
remain stable.

## Baseline

Baseline details are recorded in `docs/baseline_report.md`.

Key baseline:

- final DB: `data/full_2011plus_metadata_filter_ready_2026-05-04.sqlite`
- SHA-256:
  `366BDFE3AC9F1121C06D138EF096B49AFF4AA0D050485E6061CDF9DACC3CA27D`
- `tests = 3900`
- `vehicles = 4705`
- `source_payloads = 66477`
- `test_filter_summary = 3900`
- `accounted_for_count = 3900`
- `known_false_positive_count = 0`
- `unadjudicated_count = 0`

## Regression Tests Added Or Strengthened

- `tests/test_filter_db_materializer.py` now asserts stable vehicle field
  promotion counts and read-model report counts.
- `tests/test_smoke.py` now asserts default settings are defined by
  `nhtsa_metadata.constants`.

## Validation Commands

Final validation was performed with:

```powershell
pytest tests\test_filter_db_materializer.py -q
pytest tests\test_smoke.py -q
pytest -q
ruff check .
mypy src\nhtsa_metadata
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
powershell -ExecutionPolicy Bypass -File .harness\run.ps1
```

## Materialized DB Regression Comparison

The filter-ready DB was regenerated after the materializer refactor and
compared against the accepted baseline DB. This check was local-only and did not
call live NHTSA APIs.

Regeneration command:

```powershell
python -m nhtsa_metadata.cli schema materialize-filter-db --source-db data\full_2011plus_metadata_only_refresh_2026-05-03.sqlite --output-db data\refactor_validation_filter_ready_2026-05-07.sqlite --overwrite
```

Comparison inputs:

| Item | Path |
|---|---|
| Baseline filter-ready DB | `data/full_2011plus_metadata_filter_ready_2026-05-04.sqlite` |
| Refactored regenerated DB | `data/refactor_validation_filter_ready_2026-05-07.sqlite` |

Materialization report:

| Metric | Value |
|---|---:|
| `vehicle_rows` | 4705 |
| `vehicle_changed_rows` | 4694 |
| `test_rows` | 3900 |
| `test_filter_summary_rows` | 3900 |
| `has_load_cell_barrier_count` | 1149 |
| `load_cell_classified_test_count` | 1137 |
| `channel_map_rows_materialized` | 0 |

DB-level comparison:

| Check | Baseline | Refactored | Result |
|---|---:|---:|---|
| File size bytes | 2762768384 | 2762747904 | differs |
| Table count | 42 | 42 | passed |
| Table list | same | same | passed |
| Schema hash | `f0707e528a0d602662af71f88ade6e2c121d9de3f56a274433c71dbb0ed0de04` | `f0707e528a0d602662af71f88ade6e2c121d9de3f56a274433c71dbb0ed0de04` | passed |
| Per-table row counts | no differences | no differences | passed |
| `tests` columns | 26 | 26 | passed |
| `vehicles` columns | 32 | 32 | passed |
| `test_filter_summary` columns | 34 | 34 | passed |

File SHA-256:

| DB | SHA-256 |
|---|---|
| Baseline | `366BDFE3AC9F1121C06D138EF096B49AFF4AA0D050485E6061CDF9DACC3CA27D` |
| Refactored regenerated | `15635FC810839CF34FEFA7FBFDEECD8A3E940B81A2606D5635BE2BD864051367` |

The full file hash differs. The structure, row counts, selected logical hashes,
and scope checks below show no data-shape or accounting regression. The
remaining difference is the expected barrier load-cell classification config
version tag update from `2.2.2-db2011plus-shape-normalized-metadata-explicit-final`
to `2.2.3-db2011plus-stage-l-read-model-integration-final`.

Selected logical hashes:

| Surface | Result | Hash |
|---|---|---|
| `tests` | passed | `1d5cbd0db1bbb0eca5930689a5575f34ba66b62b6ebdd35266f723d865fd6294` |
| `vehicles` | passed | `4901bdcae331a369ee64b624c720edf5a962e2da68d91247bcc4fbbab5f55e65` |
| `source_payloads` | passed | `4a0c2246d489c4c0c9f398a2566eea059d554aebe828d170a8878873f6afe793` |
| `test_filter_summary`, normalized excluding version/timestamps | passed | `6004386cd92b264296e3d7d67a0e0fd7e89a310664374bd4514c126160d8d949` |
| `barrier_load_cell_classification`, normalized excluding version/timestamps and `evidence_json.config_version` | passed | `2e0208fc7ec3f3406f1fa4d2b0b953409e5d1eeae9d512f7d155b9c000c8cb84` |

Scope and key-integrity checks:

| Check | Baseline | Refactored | Result |
|---|---:|---:|---|
| `tests` date range | `2011-01-03` to `2025-11-19` | `2011-01-03` to `2025-11-19` | passed |
| `tests` count | 3900 | 3900 | passed |
| `tests` before `2011-01-01` | 0 | 0 | passed |
| `tests` after `2026-05-04` | 0 | 0 | passed |
| duplicate `tests.test_no` groups | 0 | 0 | passed |
| null `tests.test_no` | 0 | 0 | passed |
| null `tests.test_date` | 0 | 0 | passed |
| null `vehicles.test_id` | 0 | 0 | passed |
| null `vehicles.test_no` | 0 | 0 | passed |
| null `source_payloads.test_no` | 0 | 0 | passed |
| null `test_filter_summary.test_no` | 0 | 0 | passed |

Known expected difference:

| Difference | Rows | Interpretation |
|---|---:|---|
| `test_filter_summary.load_cell_barrier_config_version` | 1137 | expected config version tag update only |
| `barrier_load_cell_classification.config_version` | 1137 | expected config version tag update only |
| `barrier_load_cell_classification.evidence_json` | 1137 | expected because `evidence_json.config_version` changed with the same config tag |

Conclusion: the refactored materializer reproduces the baseline schema, table
set, row counts, scope, key integrity, and normalized logical content. The DB
file hash is not identical because the current branch intentionally uses the
later barrier load-cell config version tag in regenerated read-model rows.

## Final Results

| Command | Result |
|---|---|
| `pytest tests\test_docs_contract.py tests\test_filter_db_materializer.py tests\test_smoke.py -q` | passed, `11 passed, 1 warning` |
| `ruff check .` | passed |
| `mypy src\nhtsa_metadata` | passed, `55 source files` |
| `pytest -q` | passed, `136 passed, 4 warnings` |
| `powershell -ExecutionPolicy Bypass -File scripts\verify.ps1` | passed |
| `powershell -ExecutionPolicy Bypass -File .harness\run.ps1` | passed |

The 4 warnings are the existing `TestFilterSummary` pytest collection warnings.
They are pre-existing, non-blocking warnings and are not caused by this
refactoring.

## Result

The refactoring pass is locally accepted based on the recorded verification
commands and materialized DB comparison. It preserves project behavior, keeps
final accepted metrics stable, and leaves the repository in a verification-green
state.
