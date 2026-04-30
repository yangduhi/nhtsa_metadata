# Full-Scale 2011+ Crawler Approval Package

## Status

This is an approval package only. It does not approve or execute a full crawler.

## Current Pass Evidence

- 2011+ scope gate passed.
- 1000-test bounded live pilot passed.
- 500 additional actual-crash tests were collected without overlap, bringing the local cumulative DB to 1500 tests.
- Endpoint completeness after 1500 tests has missing matrix count 0.
- Schema audit has scope violations 0 and duplicate groups 0 for the seven canonical duplicate targets.
- Schema optimization P0/P1 remains 0/0.
- Data package candidates are fully classified without downloading files.
- Default verify/harness remains fixture/mock only.

## Accepted Warnings

- `dummy_type` facet is absent and accepted as a warning until stable non-null values are observed.
- P2/P3 backlog remains for optional dictionary/index/facet refinement.
- Some source conflicts are benign alias or numeric rounding differences.
- SQLite index policy remains conservative until query measurements justify more indexes.

## Expected Universe Size Estimate

Reference and live pilots indicate a multi-thousand-test 2011+ universe. The exact full-scale size must be established by a manifest-only dry run using `testDateFrom=2011-01-01`, not by `test_no` range scanning or `modelYear` filters.

## Boundary Rules

- No file download.
- No media URL fetch/download.
- No waveform parsing.
- No TDMS/UDS/EV/ABF/ISO/ZIP internal parsing.
- Raw payloads and observations remain the source of truth.
- Canonical/read-model can be dropped and rebuilt.
- `data/` artifacts are never committed.

## Rate Limit / Retry / Resume Policy

Proposed defaults for owner approval:

- bounded page size for discovery
- fixed delay between endpoint calls
- retry only transient network/server failures
- no retry for scope/out-of-scope skips
- resume by `source_payloads` and endpoint completeness audit
- backfill missing endpoint matrix only after collection completes

## Backup Policy

Before full-scale execution:

- copy the current SQLite DB to a timestamped backup path
- write manifest to `data/` and keep it ignored
- record git commit and command options in a phase report
- do not overwrite the 1500-test pilot DB

## Staged Execution Plan

Stage A: dry-run / manifest only.

Stage B: optional 250-test bounded validation if owner requests it.

Stage C: 1000-test parity check from existing manifest, no new collect.

Stage D: full 2011+ collect, approval required. Do not run in this phase.

Stage E: post-run rebuild, endpoint completeness audit, schema audit, schema optimization, scale report, API smoke.

## Stop Conditions

Stop before or during full-scale if any occurs:

- manifest contains pre-2011 rows
- missing/parse-failed test date appears in canonical rows
- `--source live` works without both `--allow-live` and `NHTSA_METADATA_ALLOW_LIVE=true`
- full crawler tries to download files
- endpoint matrix grows without a bound or resume point
- source_payloads are not saved
- canonical rebuild fails from stored raw payloads
- duplicate groups become non-zero
- semantic hard failures become non-zero
- P0/P1 schema recommendation appears
- P0/P1 source conflict appears
- data artifacts become staged/tracked

## Post-Run Audit Matrix

Required after full-scale:

- endpoint completeness
- schema audit with duplicate details
- scope audit
- semantic cardinality audit
- data package classification audit
- restraint/intrusion/instrumentation scheduling audit
- schema optimization report
- scale report
- API smoke using local DB

## Approval Decision Needed

Owner must separately approve Stage D before any full-scale collection is run.
