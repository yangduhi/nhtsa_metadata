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

The harness delegates to `scripts/verify.ps1` in Phase 0.

## Live API Policy

Live API access is disabled by default. Manual live validation commands require explicit live
opt-in. Default tests and verification scripts must remain fixture/mock only.

이 프로젝트의 canonical/read-model 대상은 test_date >= 2011-01-01인 NHTSA crash test metadata로 제한한다.
modelYear는 scope 판단 기준이 아니다.
test_date missing 또는 parse 실패 record는 기본적으로 canonical/read-model에서 제외한다.

## Bounded Pilot Commands

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog build-manifest `
  --source live `
  --allow-live `
  --output data\stratified_live_pilot_2011plus_manifest.csv `
  --limit 40 `
  --max-per-configuration 5 `
  --min-test-date 2011-01-01 `
  --reference-database D:\vscode\pulse_analysis\data\db\nhtsa_data.db

powershell -ExecutionPolicy Bypass -File scripts\live_pilot_validate.ps1 `
  -AllowLive `
  -DatabaseUrl sqlite:///data/stratified_live_pilot_2011plus.sqlite `
  -Manifest data/stratified_live_pilot_2011plus_manifest.csv
```

The reference database is only a bounded manifest seed. Live metadata collection still happens
through NHTSA endpoints, and the pilot remains bounded by manifest. It must not be treated as a
full crawler.

Schema audit can include duplicate details without raw payload text:

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli schema audit `
  --database-url sqlite:///data/stratified_live_pilot_2011plus.sqlite `
  --output data\schema_audit_report_2011plus.json `
  --include-duplicate-details
```

After parser or canonical dedupe changes, an existing pilot DB can be rebuilt from stored
`source_payloads` without live calls:

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog rebuild `
  --database-url sqlite:///data/stratified_live_pilot.sqlite
```

When `--test-no` is omitted, rebuild uses distinct test numbers already present in
`source_payloads`.

## Source Contract Documents

Phase 1 requires these documents:

- `docs/source_contract.md`
- `docs/source_endpoint_matrix.md`
- `docs/source_field_aliases.md`
- `docs/source_anomalies.md`
- `docs/catalog_builder_contract.md`
- `docs/filtering_contract.md`
- `docs/field_coverage_contract.md`
- `docs/db_schema_contract.md`
