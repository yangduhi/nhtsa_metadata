# 2011+ Scope Gate Report

## Scope

- Restrict canonical/read-model rows to `test_date >= 2011-01-01`.
- Use `test_date`, not `modelYear`, for scope.
- Exclude missing or failed test dates from canonical/read-model output.
- Do not implement a full crawler, larger pilot, file download, or waveform/data-package parsing.

## Completed

- Added `NHTSA_METADATA_MIN_TEST_DATE` / `Settings.min_test_date`.
- Added optional `NHTSA_METADATA_REFERENCE_DB_PATH` / `catalog build-manifest --reference-database`
  seed input for bounded pilot manifest construction from a local legacy SQLite catalog.
- Added scope evaluation for source payloads and canonical specs.
- Added collect-time guard that records `collection_run_items.status = skipped_out_of_scope`.
- Added rebuild-time guard that removes stale out-of-scope canonical rows.
- Updated manifest builder to emit 2011+ columns and pass `testDateFrom` to live by-search.
- Added schema audit scope summary, hard failure exit for scope violations, and restraint
  scheduling summary.
- Added API/detail guard for stale out-of-scope canonical rows.
- Reclassified fixture manifest paths into `in_scope/` and `out_of_scope_legacy/`.
- Added configuration bucket aliases for `VTB`, `ITV`, and `VTP` so local reference rows do not
  bypass `--max-per-configuration`.

## Reference DB Findings

Source: `D:\vscode\pulse_analysis\data\db\nhtsa_data.db`

- `crash_tests`: 4,513 rows.
- Parseable `test_date`: 4,344 rows.
- Missing `test_date`: 169 rows.
- 2011+ parseable rows: 3,888.
- Pre-2011 parseable rows: 456.
- Earliest 2011+ row by `test_date`: `test_no=7201`, `test_date=2011-01-03`,
  `crash_type=VEHICLE INTO BARRIER`.
- Latest pre-2011 row by date in the local catalog: `test_no=7200`,
  `test_date=2010-12-20`, `crash_type=VEHICLE INTO BARRIER`.
- Test number is not a reliable scope boundary by itself; `test_date` remains the only scope
  criterion.

## Verification

- pytest: passed (`83 passed`, 2 existing collection warnings).
- ruff: passed for `src` and `tests`.
- mypy: passed for `src\nhtsa_metadata`.
- scripts/verify.ps1: passed (`83 passed`, 2 existing collection warnings).
- .harness/run.ps1: passed (`83 passed`, 2 existing collection warnings).
- 2011+ live pilot: passed with 40 manifest rows and 40 succeeded collection run items.
- schema audit: passed with exit code 0 on `data/schema_audit_report_2011plus.json`.

## 2011+ Live Pilot Summary

- Manifest: `data/stratified_live_pilot_2011plus_manifest.csv`.
- Database: `data/stratified_live_pilot_2011plus.sqlite`.
- Audit report: `data/schema_audit_report_2011plus.json`.
- Manifest rows: 40.
- Manifest date range: `2011-01-03` to `2016-12-14`.
- Required baselines included: `10001`, `10003`.
- Earliest 2011+ seed included: `7201`.
- Max normalized configuration bucket count: 5.
- Source payloads: 548.
- Source payload observations: 548.
- Canonical tests: 40.
- Read-model filter summaries: 40.
- Instrumentation channels: 3,266.
- Media assets: 2,143.
- Duplicate groups: 0 for vehicles, test_participants, barriers, occupants, restraints,
  instrumentation_channels, media_assets.
- Scope violations: 0.
- Read-model out-of-scope rows: 0.
- Data package candidates: 200.
- Classified data packages: 200.
- Unclassified asset candidates: 0.
- Restraint info expected/actual payloads: 48/48.
- Restraint info missing requests: 0.
- `10001`: 1 vehicle, 2 participants, 2 barriers, 4 canonical occupant rows, 3 restraints,
  634 instrumentation channels, 105 media assets.
- `10003`: 2 vehicles, participant kinds `subject_vehicle` and `impactor_vehicle`, 0 barriers,
  4 canonical occupant rows, 4 restraints, 63 instrumentation channels, 152 media assets.

## Live Policy

- Default verification remains fixture/mock only.
- 2011+ live pilot output paths are under `data/` and remain ignored.
- Full crawler and file download were not executed.
