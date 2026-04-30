# Operations

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
  --markdown-output docs/phase_reports/schema_v1_0_backlog_triage.md `
  --summary-output docs/phase_reports/schema_v1_0_backlog_summary.md
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

- `docs/source_contract.md`
- `docs/source_endpoint_matrix.md`
- `docs/source_field_aliases.md`
- `docs/source_anomalies.md`
- `docs/catalog_builder_contract.md`
- `docs/filtering_contract.md`
- `docs/field_coverage_contract.md`
- `docs/db_schema_contract.md`
