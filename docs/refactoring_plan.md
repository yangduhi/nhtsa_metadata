# Refactoring Plan

## Goal

Improve post-delivery maintainability without changing functional behavior,
output DB semantics, output file formats, accepted metrics, or verification
contracts.

## Non-Goals

- No new NHTSA data source.
- No live API call.
- No final DB schema semantic change.
- No output column rename.
- No GUI/API productization.
- No broad rewrite of historical Stage D/F scripts.
- No push or merge to `main`.

## Current Structure

Current high-level structure:

```text
src/nhtsa_metadata/
  api/                 FastAPI app and route definitions
  db/                  SQLAlchemy models, sessions, migration helpers
  services/            catalog, schema, classification, read-model, and reports
  sources/nhtsa_crash/ NHTSA endpoint definitions, clients, parsers, fixtures
  cli.py               Typer command entrypoint
```

The project already has a clear raw/provenance -> canonical -> read-model
direction. The refactoring target is therefore local responsibility separation,
not a new architecture.

## Target Structure For This Pass

This pass will keep the existing package layout and make only low-risk local
separations:

```text
src/nhtsa_metadata/services/
  filter_db_materializer.py      DB copy/materialization orchestration
  vehicle_filter_fields.py       vehicle field promotion helpers
  filter_db_reports.py           filter-ready DB report helpers
```

The public CLI command and materializer return payload must remain compatible.

## Work Order

1. Capture baseline and audit documents.
2. Commit baseline/audit/plan documentation.
3. Extract vehicle filter-field promotion from `filter_db_materializer.py`.
4. Extract filter DB read-model report construction from
   `filter_db_materializer.py`.
5. Add or update tests around materializer behavior and report shape.
6. Run targeted tests first.
7. Run full project verification.
8. Write final refactoring and validation reports.
9. Commit final docs.

## Invariants

The following must remain unchanged:

- Final DB row counts and scope.
- Output table/column names.
- `materialize_filter_database` public function name and return keys.
- CLI command names.
- Default verification behavior.
- Live API guardrails.

## Regression Checks

Required checks:

```powershell
pytest tests\test_filter_db_materializer.py -q
pytest -q
ruff check .
mypy src\nhtsa_metadata
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
powershell -ExecutionPolicy Bypass -File .harness\run.ps1
```

The output DB itself is large and ignored. For this refactoring pass, baseline
compatibility is checked through:

- stable materializer result payload keys;
- stable fixture test behavior;
- tracked accounting and lineage fixture counts;
- final verification commands.

## Risks

- Broad service decomposition could create import churn. This pass avoids that.
- Historical scripts contain absolute paths. This pass documents them but does
  not rewrite them.
- Some long functions are untouched. They remain future improvement candidates.
