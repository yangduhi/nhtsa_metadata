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

Final validation will use:

```powershell
pytest tests\test_filter_db_materializer.py -q
pytest tests\test_smoke.py -q
pytest -q
ruff check .
mypy src\nhtsa_metadata
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
powershell -ExecutionPolicy Bypass -File .harness\run.ps1
```

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

The refactoring pass is accepted. It preserves project behavior, keeps final
accepted metrics stable, and leaves the repository in a verification-green
state.
