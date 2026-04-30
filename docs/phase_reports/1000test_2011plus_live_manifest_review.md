# 1000-Test 2011+ Live Manifest Review

## Scope
- Source: live by-search with reference DB enrichment only.
- Minimum test date: 2011-01-01.
- Balance policy: type-year, type-first, relax-balance.
- Full crawler: no.
- File download: no.

## Command
```powershell
$env:NHTSA_METADATA_ALLOW_LIVE="true"
.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog build-manifest `
  --source live `
  --allow-live `
  --output data\stratified_live_pilot_2011plus_1000_manifest.csv `
  --limit 1000 `
  --min-test-date 2011-01-01 `
  --year-from 2011 `
  --year-to 2026 `
  --balance-strategy type-year `
  --balance-priority type-first `
  --relax-balance `
  --reference-database D:\vscode\pulse_analysis\data\db\nhtsa_data.db
```

## Hard Gate Result
- Rows: 1000
- Duplicate test_no: 0
- Missing test_date: 0
- Pre-2011 rows: 0
- Scope status values: {'in_scope': 1000}
- Date range: 2011-01-03 to 2025-09-23
- Anchors: 7201=True, 10001=True, 10003=True
- Blank test_configuration_key: 0
- Collect may proceed: yes

## Balance Result
- Balance status: {'relaxed_missing_year': 1000}
- Relaxed reason: 2026 live/reference candidate coverage was absent for the bounded set, so rows are marked `relaxed_missing_year`.

## Year Distribution
- 2011: 57
- 2012: 57
- 2013: 124
- 2014: 57
- 2015: 57
- 2016: 73
- 2017: 131
- 2018: 56
- 2019: 56
- 2020: 56
- 2021: 56
- 2022: 55
- 2023: 55
- 2024: 55
- 2025: 55

## Configuration Distribution
- VEHICLE INTO BARRIER: 92
- IMPACTOR INTO VEHICLE: 90
- LOW RISK DEPLOYMENT: 90
- PEDESTRIAN: 90
- ROLLOVER: 90
- SLED WITH VEHICLE BODY: 90
- SLED WITHOUT VEHICLE BODY: 89
- STATIC AIR BAG TEST SIDE: 89
- VEHICLE INTO POLE: 89
- UNKNOWN: 76
- FORWARD COLLISION WARNING PERFORMANCE TEST: 45
- LANE DEPARTURE WARNING PERFORMANCE TEST: 31
- OTHER: 21
- VEHICLE INTO VEHICLE: 12
- IMPACTOR INTO IMPACTOR: 6

## Test Type Distribution
- NEW CAR ASSESSMENT TEST: 250
- EXPERIMENTAL NEW CAR ASSESSMENT TEST: 111
- OCCUPANT PERFORMANCE TEST: 100
- FMVSS 208 OCCUPANT CRASH PROTECTION: 99
- FMVSS 213 CHILD RESTRAINT SYSTEMS: 81
- FMVSS 226 EJECTION MITIGATION: 76
- OPTIONAL NEW CAR ASSESSMENT TEST: 68
- RESEARCH: 57
- OTHER: 49
- OUT OF POSITION (TWG) SIDE AIRBAG DEPLOYMENT TESTS: 43
- MODIFIED VEHICLE TEST: 15
- RMDB INTO FRONT 15 DEGREE STATIONARY VEHICLE, OVERLAP=35 PERCENT: 14
- TEST PROCEDURE DEVELOPMENT: 10
- FMVSS 214 SIDE IMPACT PROTECTION: 9
- CALIBRATION TEST: 9
- RESEARCH SAFETY VEHICLE TEST: 7
- FMVSS 301 FUEL SYSTEM INTEGRITY: 2

## Candidate vs Live Comparison
- Candidate rows: 1000
- Live manifest rows: 1000
- Overlap by test_no: 667
- Live-only rows: 333
- Candidate-only rows: 333
- Field differences on overlap: {'test_date': 0, 'test_configuration': 0, 'test_configuration_key': 0, 'test_type': 0, 'model_year': 25, 'vehicle_make': 24, 'vehicle_model': 28, 'scope_status': 0}

## Decision
- Manifest hard gates passed.
- Relaxed balance is documented and does not block collect because row count, 2011+ scope, anchors, and duplicate gates passed.
