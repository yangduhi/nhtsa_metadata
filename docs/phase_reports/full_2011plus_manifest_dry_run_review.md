# Full 2011+ Manifest Dry Run Review

## Scope
- live by-search/listing manifest-only dry run.
- No detail endpoint collect, no source_payload DB insert, no file download.
- Scope is `test_date >= 2011-01-01`; `test_no` and `modelYear` are not scope boundaries.

## Command
```powershell
$env:NHTSA_METADATA_ALLOW_LIVE="true"
.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog build-manifest `
  --source live `
  --allow-live `
  --output data\full_2011plus_manifest.csv `
  --min-test-date 2011-01-01 `
  --full-scope `
  --manifest-only `
  --rate-limit-delay-seconds 0.25 `
  --reference-database D:\vscode\pulse_analysis\data\db\nhtsa_data.db
```

## Hard Gate
- row count: 3260
- date range: 2011-01-03 to 2021-12-02
- duplicate test_no: 0
- missing/parse-failed date in output: 0
- pre-2011 rows: 0
- scope_status values: ['in_scope']
- anchors: 7201=True, 10001=True, 10003=True

## Year Distribution
- 2011: 345
- 2012: 434
- 2013: 470
- 2014: 360
- 2015: 249
- 2016: 411
- 2017: 321
- 2018: 158
- 2019: 184
- 2020: 185
- 2021: 143

## Test Type Distribution
- NEW CAR ASSESSMENT TEST: 1061
- OPTIONAL NEW CAR ASSESSMENT TEST: 346
- EXPERIMENTAL NEW CAR ASSESSMENT TEST: 330
- FMVSS 208 OCCUPANT CRASH PROTECTION: 327
- FMVSS 213 CHILD RESTRAINT SYSTEMS: 266
- OCCUPANT PERFORMANCE TEST: 181
- RMDB INTO FRONT 15 DEGREE STATIONARY VEHICLE, OVERLAP=35 PERCENT: 145
- RESEARCH SAFETY VEHICLE TEST: 128
- OTHER: 91
- RESEARCH: 76
- FMVSS 226 EJECTION MITIGATION: 76
- OUT OF POSITION (TWG) SIDE AIRBAG DEPLOYMENT TESTS: 71
- TEST PROCEDURE DEVELOPMENT: 55
- MODIFIED VEHICLE TEST: 25
- RMDB INTO FRONT 7 DEGREE STATIONARY VEHICLE, OVERLAP=20 PERCENT: 18
- FMVSS 301 FUEL SYSTEM INTEGRITY: 18
- FMVSS 214 SIDE IMPACT PROTECTION: 13
- Validation New Car Assessment Test: 9
- CALIBRATION TEST: 9
- VALIDATION NEW CAR ASSESSMENT TEST: 8
- FMVSS COMPLIANCE TEST - UNSPECIFIED: 7

## Test Configuration Distribution
- IMPACTOR INTO VEHICLE: 648
- VEHICLE INTO BARRIER: 571
- VEHICLE INTO POLE: 457
- SLED WITHOUT VEHICLE BODY: 446
- LOW RISK DEPLOYMENT: 261
- STATIC AIR BAG TEST SIDE: 235
- PEDESTRIAN: 195
- ROLLOVER: 130
- SLED WITH VEHICLE BODY: 126
- UNKNOWN: 76
- FORWARD COLLISION WARNING PERFORMANCE TEST: 45
- LANE DEPARTURE WARNING PERFORMANCE TEST: 31
- OTHER: 21
- VEHICLE INTO VEHICLE: 12
- IMPACTOR INTO IMPACTOR: 6

## Classification Distribution
- airbag_static_or_low_risk: 496
- frontal_barrier: 571
- non_crash_adas: 76
- pole: 457
- rollover: 130
- side_impactor: 648
- sled: 572
- unknown_or_other: 298
- vehicle_to_vehicle: 12

## Reference DB Discrepancy Summary
- reference DB 2011+ rows: 3888
- live manifest rows: 3260
- overlap: 3260
- reference-only rows: 628
- live-only rows: 0
- reference year range: 2011 to 2025
- live manifest year range: 2011 to 2021
- observed discrepancy: live by-search manifest has no 2022-2025 rows, while the existing 1500 actual-crash DB has 2022-2025 rows.
- decision impact: full-scale Stage D needs an explicit discovery authority decision before execution.

## Statement
- Detail endpoint collect: not executed.
- Full crawler: not executed.
- File/media download: not executed.
