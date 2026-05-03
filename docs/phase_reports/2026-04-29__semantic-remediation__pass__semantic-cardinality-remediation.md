# 2026-04-29 | Semantic remediation | PASS | Semantic Cardinality Remediation

﻿# Semantic Cardinality Remediation

## Scope

This report records the 2011+ 40-test pilot semantic cardinality remediation. It does not include
full crawler work, 100/250-test pilot collection, file downloads, or waveform/package parsing.

## Implementation Decision

The selected model is occupant-context canonical restraints, not a separate assignment table.

- `occupants` are normalized occupant slots.
- `restraints` are occupant-context restraint assignments.
- `restraint_info` request context is preserved when NHTSA payload rows omit occupant location.
- `barriers` dedupe normalized barrier identity across `metadata_export` and `barrier_info`.
- Raw `source_payloads`, observations, field catalog, and `canonical_row_sources` remain source-of-truth/provenance layers.

## Code Changes

- Parser enriches `restraint_info` canonical rows with request `test_no`, `vehicle_no`, and `occupant_location` when missing from the response row.
- Rebuild reconstructs stored payload requests with `occupant_location_raw` so stored raw payloads can rebuild the same occupant context without live calls.
- Restraints now carry:
  - `occupant_location_normalized`
  - `restraint_subject_kind`
  - `restraint_subject_semantic_key`
  - `restraint_subject_semantic_hash`
  - `semantic_key`
  - `semantic_hash`
- Occupant location aliases normalize metadata codes such as `01`/`02` and API labels such as `LEFT FRONT SEAT`/`RIGHT FRONT SEAT` to stable slots.
- Schema audit now reports `semantic_cardinality` and `barrier_semantic_cardinality` and fails on semantic hard failures.

## 40-Test DB Rebuild

Command:

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog rebuild `
  --database-url sqlite:///data/stratified_live_pilot_2011plus.sqlite
```

Result:

- canonical rows rebuilt: 6480
- tests rebuilt: 40
- live API calls: none

Schema audit command:

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli schema audit `
  --database-url sqlite:///data/stratified_live_pilot_2011plus.sqlite `
  --output data/schema_audit_report_2011plus_after_semantic_fix.json `
  --include-duplicate-details `
  --duplicate-detail-limit 50
```

Result:

- exit code: 0
- scope violations: 0
- read-model out-of-scope rows: 0
- semantic hard failures: 0
- duplicate groups: 0 for vehicles, test participants, barriers, occupants, restraints, instrumentation channels, and media assets
- data package candidates/classified: 200/200
- unclassified asset candidates: 0
- restraint_info expected/actual payloads: 48/48
- restraint_info missing requests: 0

## Key DB Counts

- tests: 40
- source_payloads: 548
- source_payload_observations: 548
- collection_runs: 1
- canonical_row_sources: 10021
- occupants: 48
- restraints: 101
- barriers: 17
- instrumentation_channels: 3266
- media_assets: 2143
- test_filter_summary: 40

## Baseline Results

10001:

- vehicles: 1
- participants: subject_vehicle 1, barrier 1
- barriers: 1
- barrier semantic status: fixed
- occupants: 2
- normalized occupant slots: 2
- restraints: 6
- occupant-specific restraint assignments: 6
- restraint context loss: 0
- instrumentation_channels: 634
- media_assets: 105

10003:

- vehicles: 2
- participants: subject_vehicle 1, impactor_vehicle 1
- barriers: 0
- occupants: 2
- normalized occupant slots: 2
- restraints: 6
- occupant-specific restraint assignments: 6
- restraint context loss: 0
- instrumentation_channels: 63
- media_assets: 152

## Verification

- `pytest -q`: 84 passed
- `ruff check src tests`: passed
- `mypy src\nhtsa_metadata`: passed
- `scripts\verify.ps1`: passed
- `.harness\run.ps1`: passed
- live safety negative without `--allow-live`: failed as expected, no output manifest created
- live safety negative without `NHTSA_METADATA_ALLOW_LIVE`: failed as expected, no output manifest created

## Decision

Semantic remediation passes for the existing 2011+ 40-test pilot DB.

A 100-test bounded 2011+ pilot may be planned next, but it still requires separate approval before
live execution. Full crawler and file downloads remain out of scope.
