# Live Pilot Remediation Report

## Scope

- Remediate bounded live pilot partial-pass findings before any larger manifest pilot.
- Do not implement a full crawler.
- Do not download files or parse waveform/data packages.
- Keep default verification fixture/mock only.

## Completed

- Added restraint semantic identity and canonical dedupe by `(test_id, semantic_hash)`.
- Made duplicate restraint observations attach through `canonical_row_sources`.
- Added JSON-safe source conflict recording for canonical value conflicts.
- Extended schema audit duplicate summaries to vehicles, test participants, barriers, occupants,
  restraints, instrumentation channels, and media assets.
- Added optional schema audit duplicate details with a configurable limit.
- Added asset subtype classification for UDS, EV, ABF, ISO, TDMS, ZIP, PDF, HTML, and UNKNOWN.
- Classified vehicle document data-package candidates as `asset_kind = data_package` with
  `asset_subtype`.
- Updated fixture collection to derive `restraint_info` requests from `occupant_info` instead
  of trusting summary links.
- Added rebuild-all behavior for `catalog rebuild` when `--test-no` is omitted.

## Verification

- ruff: pass
- mypy: pass
- pytest: pass (`74 passed`)
- scripts/verify.ps1: pass (`74 passed`)
- .harness/run.ps1: pass (`74 passed`)

## Live Policy

- No live API calls are added to default tests, `scripts/verify.ps1`, or `.harness/run.ps1`.
- Existing pilot DB remediation can be validated by rebuilding from stored `source_payloads`.

## Remaining Manual Check

- Rebuild the existing 25-test pilot DB and write `data/schema_audit_report_after_restraint_fix.json`.
- If endpoint scheduling must be validated against live responses, rerun only the same bounded
  manifest, not a larger pilot.
