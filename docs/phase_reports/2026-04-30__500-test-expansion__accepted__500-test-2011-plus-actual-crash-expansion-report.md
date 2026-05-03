# 2026-04-30 | 500-test expansion | ACCEPTED | 500-Test 2011+ Actual Crash Expansion Report

## Scope

- Date: 2026-04-30
- Branch: `codex/500test-actual-crash-expansion`
- Scope: add 500 bounded live metadata tests that are actual crash configurations.
- Minimum test date: `2011-01-01`
- Full crawler: not run.
- File download: not run.
- Media URL fetch/download: not run.
- Waveform/package parsing: not run.

## Actual Crash Selection Rule

The added manifest used `--actual-crash-only` and accepted only these normalized `test_configuration` values:

- `IMPACTOR INTO VEHICLE`
- `ROLLOVER`
- `VEHICLE INTO BARRIER`
- `VEHICLE INTO POLE`
- `VEHICLE INTO VEHICLE`

The manifest excluded the existing 1000-test manifest, so the 500 added tests do not overlap with `data/stratified_live_pilot_2011plus_1000_manifest.csv`.

Non-crash or non-vehicle-impact configurations such as ADAS performance tests, low risk deployment, static airbag, pedestrian, sled, unknown/other, and impactor-into-impactor were not eligible for the added manifest.

## Commands

Manifest build:

```powershell
$env:NHTSA_METADATA_ALLOW_LIVE="true"

.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog build-manifest `
  --source live `
  --allow-live `
  --output data\stratified_live_pilot_2011plus_500_actual_crash_manifest.csv `
  --limit 500 `
  --min-test-date 2011-01-01 `
  --year-from 2011 `
  --year-to 2026 `
  --balance-strategy type-year `
  --balance-priority type-first `
  --relax-balance `
  --actual-crash-only `
  --no-include-required-baselines `
  --exclude-manifest data\stratified_live_pilot_2011plus_1000_manifest.csv `
  --reference-database D:\vscode\pulse_analysis\data\db\nhtsa_data.db
```

Collect:

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog collect `
  --manifest data\stratified_live_pilot_2011plus_500_actual_crash_manifest.csv `
  --database-url sqlite:///data/stratified_live_pilot_2011plus_1500_actual_crash.sqlite `
  --source live `
  --allow-live
```

Intrusion backfill for the new 500 manifest:

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog backfill-endpoints `
  --database-url sqlite:///data/stratified_live_pilot_2011plus_1500_actual_crash.sqlite `
  --manifest data\stratified_live_pilot_2011plus_500_actual_crash_manifest.csv `
  --source live `
  --allow-live `
  --endpoints intrusion_info `
  --scope existing-manifest `
  --only-missing `
  --min-test-date 2011-01-01 `
  --output data\backfill_intrusion_2011plus_500_actual_crash_report.json
```

## Manifest Result

- New manifest path: `data/stratified_live_pilot_2011plus_500_actual_crash_manifest.csv`
- Combined manifest path: `data/stratified_live_pilot_2011plus_1500_actual_crash_combined_manifest.csv`
- New manifest rows: 500
- Duplicate `test_no`: 0
- Overlap with existing 1000 manifest: 0
- Missing test date rows: 0
- Pre-2011 rows: 0
- Non-actual-crash configuration rows: 0
- Date range: `2011-01-04` to `2024-08-12`
- Balance status: `relaxed_missing_year` for all rows because no eligible 2025/2026 actual-crash live rows were available in the bounded candidate set.

Configuration distribution:

| Configuration | Count |
|---|---:|
| `IMPACTOR INTO VEHICLE` | 154 |
| `VEHICLE INTO BARRIER` | 153 |
| `VEHICLE INTO POLE` | 153 |
| `ROLLOVER` | 40 |

Year distribution:

| Year | Count |
|---|---:|
| 2011 | 36 |
| 2012 | 35 |
| 2013 | 52 |
| 2014 | 35 |
| 2015 | 35 |
| 2016 | 35 |
| 2017 | 34 |
| 2018 | 34 |
| 2019 | 34 |
| 2020 | 34 |
| 2021 | 34 |
| 2022 | 34 |
| 2023 | 34 |
| 2024 | 34 |

## Collection Result

- Collection database: `data/stratified_live_pilot_2011plus_1500_actual_crash.sqlite`
- Existing 1000-test DB was copied first; the 500-test actual-crash manifest was collected into the copied 1500-test DB.
- New 500-test collection run ID: 4
- New 500-test collection status: succeeded
- New collection run items: 500 succeeded, 0 failed
- Intrusion backfill run ID: 5
- Intrusion backfill fetched: 522
- Intrusion backfill failed: 0
- No new test numbers were added by backfill.

Combined DB counts after collect and backfill:

| Table / Metric | Count |
|---|---:|
| `tests` | 1500 |
| `test_filter_summary` | 1500 |
| `source_payloads` | 25676 |
| `source_payload_observations` | 25676 |
| `collection_runs` | 5 |
| `collection_run_items` | 3422 |
| `canonical_row_sources` | 528960 |
| `vehicles` | 1758 |
| `test_participants` | 2374 |
| `barriers` | 616 |
| `occupants` | 2122 |
| `restraints` | 4384 |
| `instrumentation_channels` | 186763 |
| `media_assets` | 100632 |
| `source_field_catalog` | 511 |

## Endpoint Completeness

Combined 1500 manifest/database endpoint matrix:

| Endpoint | Expected | Actual Payloads | Missing | Allowed Empty | Non-Empty |
|---|---:|---:|---:|---:|---:|
| `test_summary` | 1500 | 1500 | 0 | 0 | 1500 |
| `metadata_export` | 1500 | 1500 | 0 | 0 | 1500 |
| `test_detail` | 1500 | 1500 | 0 | 0 | 1500 |
| `vehicle_info` | 1500 | 1500 | 0 | 0 | 1500 |
| `barrier_info` | 1500 | 1500 | 0 | 884 | 616 |
| `occupant_info` | 1500 | 1500 | 0 | 189 | 1311 |
| `multimedia_files` | 1500 | 1500 | 0 | 0 | 1500 |
| `vehicle_documents` | 1500 | 1500 | 0 | 0 | 1500 |
| `intrusion_info` | 1535 | 1535 | 0 | 1514 | 21 |
| `restraint_info` | 2010 | 2010 | 0 | 123 | 1887 |
| `instrumentation_info` | 10131 | 10131 | 0 | 5 | 10126 |

`missing_endpoint_matrix_count = 0`.

## Schema Audit Summary

- Scope violations: 0
- In-scope tests: 1500
- Out-of-scope tests: 0
- Missing canonical test date: 0
- Date parse failed: 0
- Read-model out-of-scope rows: 0
- Unmapped field count: 494
- Wildcard field path normalization confirmed, for example `$.results[*].axisDirofSensor`.

Canonical duplicate groups:

| Table | Group Count | Row Count |
|---|---:|---:|
| `vehicles` | 0 | 0 |
| `test_participants` | 0 | 0 |
| `barriers` | 0 | 0 |
| `occupants` | 0 | 0 |
| `restraints` | 0 | 0 |
| `instrumentation_channels` | 0 | 0 |
| `media_assets` | 0 | 0 |

Semantic cardinality:

| Audit | Count | Status Summary |
|---|---:|---|
| `barriers` | 616 | `fixed=616` |
| `occupant_slots` | 1311 | `pass=1311` |
| `restraint_assignments` | 1193 | `pass=1193` |
| `hard_failures` | 0 | none |

Asset classification:

- Data package candidates: 7426
- Classified data packages: 7429
- Unclassified asset candidates: 0
- Counting invariant status: pass
- Files were not downloaded; only URL/metadata registry rows were stored.

Restraint scheduling:

- Expected payload count: 2010
- Actual payload count: 2010
- Missing requests: 0

## Baseline Checks

| Test No | Vehicles | Participants | Barriers | Occupants | Restraints | Instrumentation | Media Assets | Notes |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 7201 | 1 | 2 | 1 | 2 | 4 | 227 | 102 | 2011+ canonical exists |
| 10001 | 1 | 2 | 1 | 2 | 6 | 634 | 105 | frontal/barrier baseline preserved |
| 10003 | 2 | 2 | 0 | 2 | 6 | 63 | 152 | contains `subject_vehicle` and `impactor_vehicle` |

## Safety / Git

- `data/` artifacts remain ignored and are not commit candidates.
- The implementation changed only manifest-building code/tests and this report.
- Default verify/harness paths must remain fixture/mock only; live commands above were manual and explicitly gated.
- Live safety negative check passed:
- `--source live` without `--allow-live`: failed with exit code 1 and no output file.
- `--source live --allow-live` without `NHTSA_METADATA_ALLOW_LIVE=true`: failed with exit code 1 and no output file.

Verification:

| Check | Result |
|---|---|
| `pytest -q` | 91 passed |
| `ruff check src tests` | passed |
| `mypy src\nhtsa_metadata` | passed |
| `scripts\verify.ps1` | passed |
| `.harness\run.ps1` | passed |

## Decision

Result: pass for the requested 500-test actual-crash bounded live metadata expansion.

The cumulative 1500-test DB now includes the earlier 1000-test pilot plus 500 newly collected actual-crash tests. The new 500-test slice is actual-crash-only under the strict configuration rule above; the prior 1000-test pilot still contains its earlier broader stratified categories.
