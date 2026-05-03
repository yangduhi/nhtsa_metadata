# 2026-05-03 | Documentation Management | CURRENT | Documentation Map

This folder separates stable project contracts from execution history.

## Start Here

- `2026-04-28__operations__current__operations.md`: default verification, live-access policy, data artifact policy, and operational entry points.
- `phase_reports/2026-05-03__documentation-management__current__phase-report-index.md`: chronological history of completed improvement work, decisions, gates, and phase evidence.
- `phase_reports/2026-05-03__documentation-management__current__phase-report-management.md`: rules for adding and maintaining phase reports.

## Stable Contracts

These documents describe the current intended behavior and project boundaries.
They should change only when the underlying contract changes.

- `2026-04-28__source-contract__current__source-contract.md`
- `2026-04-28__source-contract__current__source-endpoint-matrix.md`
- `2026-04-28__source-contract__current__source-field-aliases.md`
- `2026-04-28__source-contract__current__source-anomalies.md`
- `2026-04-28__contract__current__catalog-builder-contract.md`
- `2026-04-28__contract__current__filtering-contract.md`
- `2026-04-28__contract__current__field-coverage-contract.md`
- `2026-04-28__contract__current__db-schema-contract.md`
- `2026-04-28__schema__current__db-schema.md`
- `2026-04-28__schema__current__index-strategy.md`
- `2026-04-28__migration-notes__current__postgresql-migration-notes.md`

## Execution History

Phase reports are maintained as chronological records. Use the generated index
instead of browsing filenames directly:

```powershell
.venv\Scripts\python.exe scripts\build_phase_report_index.py
```

The generated outputs are:

- `phase_reports/2026-05-03__documentation-management__current__phase-report-index.md`
- `phase_reports/phase_report_manifest.csv`
