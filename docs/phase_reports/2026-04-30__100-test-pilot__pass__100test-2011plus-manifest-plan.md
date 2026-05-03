# 2026-04-30 | 100-test pilot | PASS | 100-Test 2011+ Manifest Plan

﻿# 100-Test 2011+ Manifest Plan

## Conclusion

The next 100-test bounded 2011+ pilot should remain a manifest-planning step until separately
approved for live execution. This plan does not run live manifest build, live collect, full crawler,
file download, or waveform/package parsing.

A reference-DB candidate manifest was generated as an ignored planning artifact:

```text
data/stratified_live_pilot_2011plus_100_manifest_candidate.csv
```

This file is not a collected live manifest. It is a seed candidate derived from the local reference
DB only and must be validated against NHTSA live by-search before collection.

## Current Preconditions

- Branch at start: `main`
- Required semantic remediation baseline: commit `e2eb298` or later
- 40-test 2011+ semantic remediation: passed
- Full crawler: not executed
- File download: not executed
- 100-test live collect: not executed

## Reference DB Summary

Reference DB path:

```text
D:\vscode\pulse_analysis\data\db\nhtsa_data.db
```

Reference DB role:

```text
bounded manifest seed only; not canonical source of truth
```

Observed reference DB counts from `crash_tests`:

| Item | Count |
|---|---:|
| crash_tests total | 4513 |
| parseable date rows | 4344 |
| 2011+ parseable rows | 3888 |
| pre-2011 parseable rows | 456 |
| missing date rows | 169 |
| parse failed date rows | 0 |

Earliest 2011+ seeds observed:

| test_no | test_date | test_configuration |
|---:|---|---|
| 7201 | 2011-01-03 | VEHICLE INTO BARRIER |
| 7202 | 2011-01-04 | VEHICLE INTO POLE |
| 7203 | 2011-01-05 | VEHICLE INTO BARRIER |
| 7204 | 2011-01-06 | IMPACTOR INTO VEHICLE |
| 7259 | 2011-01-07 | IMPACTOR INTO VEHICLE |

Anchor tests:

| test_no | reason | reference date | reference configuration |
|---:|---|---|---|
| 7201 | earliest 2011+ seed | 2011-01-03 | VEHICLE INTO BARRIER |
| 10001 | frontal barrier baseline | 2016-12-12 | VEHICLE INTO BARRIER |
| 10003 | side impactor baseline | 2016-12-14 | IMPACTOR INTO VEHICLE |

## Candidate Manifest Design

Candidate output:

```text
data/stratified_live_pilot_2011plus_100_manifest_candidate.csv
```

Candidate result:

| Item | Value |
|---|---:|
| rows | 100 |
| duplicate test_no | 0 |
| min test_date | 2011-01-03 |
| max test_date | 2024-01-09 |
| rows with `scope_status = in_scope` | 100 |
| 7201 included | yes |
| 10001 included | yes |
| 10003 included | yes |

Candidate required columns:

```text
test_no
test_date
year_bucket
test_configuration_key
test_configuration
test_family
classification_status
reason
scope_status
seed_source
anchor_flag
```

Candidate additional planning columns:

```text
expected_endpoint_risk
expected_media_presence
expected_data_package_presence
expected_restraint_presence
expected_occupant_presence
expected_instrumentation_tier
reference_make
reference_model
reference_model_year
reference_test_type
```

Year bucket distribution:

| year_bucket | count |
|---|---:|
| 2011-2012 | 20 |
| 2013-2014 | 20 |
| 2015-2016 | 20 |
| 2017-2018 | 14 |
| 2019-2020 | 9 |
| 2021-2022 | 9 |
| 2023+ | 8 |

Configuration bucket distribution:

| configuration_key | count |
|---|---:|
| ITV | 15 |
| SLED_NO_BODY | 14 |
| SLED_WITH_BODY | 12 |
| VTB | 9 |
| STATIC_SIDE_AIRBAG | 7 |
| VTP | 7 |
| LRD | 6 |
| ROLLOVER | 6 |
| FORWARD_COLLISION_WARNING_PERFORMANCE_TEST | 4 |
| LANE_DEPARTURE_WARNING_PERFORMANCE_TEST | 4 |
| OTHER | 4 |
| PEDESTRIAN | 4 |
| VTV | 3 |
| IMPACTOR_INTO_IMPACTOR | 2 |
| UNKNOWN | 2 |
| TRAFFIC_JAM_ASSIST | 1 |

Configured cap policy:

```text
limit = 100
min_test_date = 2011-01-01
max normalized configuration bucket <= 20
anchor tests bypass no rule except duplicate prevention
```

The generated candidate stays below the `max_per_configuration = 20` cap.

## Stratification Policy

The 100-test candidate should not be selected by simple `test_no` order. Selection should be layered
by these dimensions:

1. normalized `test_configuration`
2. inferred `test_family`
3. `year_bucket`
4. expected media/data package presence
5. expected occupant presence
6. expected instrumentation tier or pulse/instrumentation proxy

Reference candidate selection uses `(test_configuration_key, year_bucket)` round-robin sampling after
anchors. This approximates a combined-stratum cap without requiring new live CLI behavior.

Known gap:

```text
The current CLI does not support `catalog build-manifest --source reference`.
The current supported command is `--source live`, and it would call live NHTSA APIs.
```

Because of that, the candidate CSV was generated from the local SQLite reference DB as a planning
artifact, not by changing CLI behavior.

## Reference DB vs Live By-Search

The reference DB is not canonical for this project. It is useful only as a seed source for candidate
selection. The live by-search and endpoint matrix remain required before any 100-test collection.

Discrepancy tracking table for the approval step:

| field | reference_value | live_value | status | resolution |
|---|---|---|---|---|
| test_no | candidate CSV value | pending live by-search | pending | compare before live collect |
| test_date | reference DB `crash_tests.test_date` | pending live by-search `testDate` | pending | reject row if live date missing, parse failed, or pre-2011 |
| test_configuration | reference DB `crash_type` | pending live by-search `testConfiguration` | pending | prefer live for final manifest metadata |
| test_type | reference raw `TEST.TSTTYPD` when available | pending live endpoint value | pending | record drift in review table |
| model_year | reference DB `year` | pending vehicle endpoint/modelYear | pending | never use as scope criterion |
| vehicle make/model | reference DB make/model | pending vehicle endpoint values | pending | drift allowed if test_no/date/config remain valid |

## Live Commands Prepared But Not Executed

Live manifest build requires separate approval:

```powershell
$env:NHTSA_METADATA_ALLOW_LIVE="true"

.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog build-manifest `
  --source live `
  --allow-live `
  --output data\stratified_live_pilot_2011plus_100_manifest.csv `
  --limit 100 `
  --max-per-configuration 20 `
  --min-test-date 2011-01-01 `
  --reference-database D:\vscode\pulse_analysis\data\db\nhtsa_data.db
```

Live collect requires separate approval after live manifest review:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\live_pilot_validate.ps1 `
  -AllowLive `
  -DatabaseUrl sqlite:///data/stratified_live_pilot_2011plus_100.sqlite `
  -Manifest data/stratified_live_pilot_2011plus_100_manifest.csv
```

Post-collect schema audit command, also not executed in this planning task:

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli schema audit `
  --database-url sqlite:///data/stratified_live_pilot_2011plus_100.sqlite `
  --output data/schema_audit_report_2011plus_100.json `
  --include-duplicate-details `
  --duplicate-detail-limit 50
```

## Decision Gate

Proceed to live manifest build only if the owner approves:

```text
Approval required: live manifest build
Approval required: live collect
Approval required: any 250-test bounded pilot planning
Approval required: any full-scale crawler design
```
