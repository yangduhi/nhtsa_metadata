# 2026-04-28 | Operations | CURRENT | Operations

﻿# Operations

## Default Verification

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
```

This command runs linting, type checking, and tests. It must not call live NHTSA APIs.

## Harness

```powershell
powershell -ExecutionPolicy Bypass -File .harness\run.ps1
```

The harness delegates to `scripts\verify.ps1` and performs repo-local preflight checks. It must not call live NHTSA APIs.

## Scope Policy

이 프로젝트의 canonical/read-model 대상은 `test_date >= 2011-01-01`인 NHTSA crash test metadata로 제한한다.
`modelYear`는 scope 판단 기준이 아니다.
`test_date` missing 또는 parse 실패 record는 기본적으로 canonical/read-model에서 제외한다.

## Live API Policy

Live API access is disabled by default. Manual live commands require explicit opt-in: `--source live`, `--allow-live`, and `NHTSA_METADATA_ALLOW_LIVE=true`.

## Data Artifact Policy

`data/*.csv`, `data/*.sqlite`, `data/*.json`, raw dumps, downloaded files, and package contents are ignored and must not be committed.

## Phase Report History

Completed phase evidence is indexed in `docs/phase_reports/2026-05-03__documentation-management__current__phase-report-index.md`.
`docs/phase_reports/2026-05-03__documentation-management__current__phase-report-management.md` defines the naming and metadata rules for new reports.

Regenerate the report index after adding or renaming a phase report:

```powershell
.venv\Scripts\python.exe scripts\build_phase_report_index.py
```

## Schema v1.0 Local Analysis Commands

These commands are local-only when pointed at an existing SQLite DB:

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli schema rebuild-code-values `
  --database-url sqlite:///data/stratified_live_pilot_2011plus_1500_actual_crash.sqlite `
  --output data/code_values_rebuild_2011plus_1500_actual_crash.json

.venv\Scripts\python.exe -m nhtsa_metadata.cli schema optimize-analyze `
  --database-url sqlite:///data/stratified_live_pilot_2011plus_1500_actual_crash.sqlite `
  --output data/schema_optimization_report_2011plus_1500_v1_final.json `
  --include-index-candidates `
  --include-column-candidates `
  --include-facet-candidates

.venv\Scripts\python.exe -m nhtsa_metadata.cli schema backlog-triage `
  --input data/schema_optimization_report_2011plus_1500_v1_final.json `
  --output data/schema_v1_0_backlog_triage.json `
  --markdown-output docs/phase_reports/2026-04-30__schema-v1-x__recorded__schema-v1-0-backlog-triage.md `
  --summary-output docs/phase_reports/2026-04-30__schema-v1-x__accepted__schema-v1-0-backlog-summary.md
```

## Full-Scale Approval Sequence

Full-scale crawler execution is not part of default operations. Approval sequence:

1. Verify default fixture/mock checks.
2. Run live safety negative checks.
3. Review Schema v1.0 finalization reports.
4. Review full-scale approval package.
5. Owner explicitly approves full-scale Stage D.
6. Build manifest-only dry run.
7. Run approved collection with backup, delay, retry, and resume policy.
8. Run post-run endpoint completeness, schema audit, optimization, code_values rebuild, scale report, and API smoke.

## Stop Conditions

Stop if live gates are bypassed, file download starts, source payload persistence fails, pre-2011 canonical rows appear, duplicate groups become non-zero, semantic hard failures appear, P0/P1 schema/source conflicts appear, or data artifacts become staged/tracked.

## Source Contract Documents

Phase work requires these documents:

- `docs/2026-04-28__source-contract__current__source-contract.md`
- `docs/2026-04-28__source-contract__current__source-endpoint-matrix.md`
- `docs/2026-04-28__source-contract__current__source-field-aliases.md`
- `docs/2026-04-28__source-contract__current__source-anomalies.md`
- `docs/2026-04-28__contract__current__catalog-builder-contract.md`
- `docs/2026-04-28__contract__current__filtering-contract.md`
- `docs/2026-04-28__contract__current__field-coverage-contract.md`
- `docs/2026-04-28__contract__current__db-schema-contract.md`
