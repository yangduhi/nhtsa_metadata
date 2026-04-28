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

## Bounded Pilot Commands

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog build-manifest `
  --source live `
  --allow-live `
  --output data\stratified_live_pilot_manifest.csv `
  --limit 40 `
  --max-per-configuration 5

powershell -ExecutionPolicy Bypass -File scripts\live_pilot_validate.ps1 `
  -AllowLive `
  -DatabaseUrl sqlite:///data/stratified_live_pilot.sqlite `
  -Manifest data/stratified_live_pilot_manifest.csv
```

The pilot remains bounded by manifest and must not be treated as a full crawler.

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
