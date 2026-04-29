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

The harness delegates to `scripts\verify.ps1` and performs repo-local preflight checks. It must not
call live NHTSA APIs.

## Scope Policy

이 프로젝트의 canonical/read-model 대상은 `test_date >= 2011-01-01`인 NHTSA crash test metadata로 제한한다.
`modelYear`는 scope 판단 기준이 아니다.
`test_date` missing 또는 parse 실패 record는 기본적으로 canonical/read-model에서 제외한다.

## Live API Policy

Live API access is disabled by default. Manual live validation commands require explicit live
opt-in: `--source live`, `--allow-live`, and `NHTSA_METADATA_ALLOW_LIVE=true`. Default tests and
verification scripts must remain fixture/mock only.

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
  -Manifest data\stratified_live_pilot_2011plus_manifest.csv
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
  --database-url sqlite:///data/stratified_live_pilot_2011plus.sqlite
```

When `--test-no` is omitted, rebuild uses distinct test numbers already present in
`source_payloads`.

## Semantic Cardinality Gate

Before increasing pilot size, the 40-test 2011+ DB must pass schema audit semantic checks:

- `scope.violations = []` and `scope.read_model_violations = []`.
- duplicate groups for vehicles, test participants, barriers, occupants, restraints,
  instrumentation channels, and media assets are all zero.
- `semantic_cardinality.hard_failures = []`.
- `10001` normalized occupant slots equal 2.
- `10001` occupant-specific restraint assignments are at least 6.
- `10001` barrier semantic status is `fixed`, `pass`, or explicitly documented as
  `accepted_known_condition`.
- `10003` normalized occupant slots equal 2 and participant pattern includes
  `subject_vehicle` plus `impactor_vehicle`.

## 100-Test Expansion Gate

Before a 100-test bounded pilot, run gates in this order:

1. `scripts\verify.ps1`.
2. `.harness\run.ps1`.
3. Live safety negative checks.
4. Rebuild and recheck the 40-test 2011+ schema audit if the DB is available.
5. Build the 100-test manifest only.
6. Request separate approval before live collection.

Recommended 100-test manifest-only command:

```powershell
$env:NHTSA_METADATA_ALLOW_LIVE = "true"
.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog build-manifest `
  --source live `
  --allow-live `
  --output data\stratified_live_pilot_2011plus_100_manifest.csv `
  --limit 100 `
  --max-per-configuration 10 `
  --min-test-date 2011-01-01 `
  --reference-database D:\vscode\pulse_analysis\data\db\nhtsa_data.db
```

Do not run 100-test live collect until separately approved.

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
