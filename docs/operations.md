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

이 프로젝트의 제품 기능은 GUI에서 선택 asset 다운로드, DB 구축, DB 관리로 제한한다. Canonical/read-model 대상은 `test_date >= 2011-01-01`인 NHTSA crash test metadata로 제한한다.
`modelYear`는 scope 판단 기준이 아니다.
`test_date` missing 또는 parse 실패 record는 기본적으로 canonical/read-model에서 제외한다.

## Product Operations

DB 구축/관리는 로컬 SQLite DB와 ignored `data/` runtime artifacts를 대상으로 한다. 현재 keeper baseline은 다음 파일이다.

```text
data/full_2011plus_metadata_filter_ready_2026-05-04.sqlite
```

Keeper 선정 근거와 archive 위치는 `docs/db_baseline.md`에 기록한다.

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli db status
.venv\Scripts\python.exe -m nhtsa_metadata.cli db backup --output data\backup.sqlite
.venv\Scripts\python.exe -m nhtsa_metadata.cli db vacuum
```

GUI 다운로드는 DB `media_assets`에 저장된 URL/metadata에서 선택한 asset만 대상으로 한다. 기본 검증에서는 mocked download만 허용하며 실제 파일 다운로드는 사용자가 GUI/API/CLI에서 명시적으로 실행한 job에 한정한다.

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli download list-assets
.venv\Scripts\python.exe -m nhtsa_metadata.cli download enqueue --media-asset-id 1
.venv\Scripts\python.exe -m nhtsa_metadata.cli download list-jobs
```

DB materialization은 product catalog surface에 둔다.

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog materialize-filter-db `
  --source-db <source-metadata-db.sqlite> `
  --output-db data\full_2011plus_metadata_filter_ready_2026-05-04.sqlite `
  --overwrite
```

## CLI Surface Policy

Top-level help should show the product surface: `catalog`, `db`, `download`, `ops`, and `legacy`.
Historical top-level aliases `coverage`, `scale`, and `schema` remain executable for backward compatibility, but are hidden from help. Use:

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli ops coverage report
.venv\Scripts\python.exe -m nhtsa_metadata.cli ops scale report
.venv\Scripts\python.exe -m nhtsa_metadata.cli legacy schema audit
```

## Live API Policy

Live API access is disabled by default. Manual live commands require explicit opt-in: `--source live`, `--allow-live`, and `NHTSA_METADATA_ALLOW_LIVE=true`.

## Data Artifact Policy

`data/*.csv`, `data/*.sqlite`, `data/*.json`, raw dumps, downloaded files, and package contents are ignored and must not be committed.

## Schema v1.0 Local Analysis Commands

These commands are local-only when pointed at an existing SQLite DB:

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli legacy schema rebuild-code-values `
  --database-url sqlite:///data/stratified_live_pilot_2011plus_1500_actual_crash.sqlite `
  --output data/code_values_rebuild_2011plus_1500_actual_crash.json

.venv\Scripts\python.exe -m nhtsa_metadata.cli legacy schema optimize-analyze `
  --database-url sqlite:///data/stratified_live_pilot_2011plus_1500_actual_crash.sqlite `
  --output data/schema_optimization_report_2011plus_1500_v1_final.json `
  --include-index-candidates `
  --include-column-candidates `
  --include-facet-candidates

.venv\Scripts\python.exe -m nhtsa_metadata.cli legacy schema backlog-triage `
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
