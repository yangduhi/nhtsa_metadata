# Schema v1.0 Finalization Decision

## Decision

Schema v1.0 is finalized for a 2011+ NHTSA crash test metadata-only database.

Full-scale crawler readiness is `pass for approval review`, not execution approval. The full crawler was not run in this phase.

## Scope

- Canonical/read-model scope: NHTSA crash test metadata with `test_date >= 2011-01-01`.
- `test_no` is not a scope boundary because numbering is not a stable date proxy.
- `modelYear` is not a scope boundary because vehicle model year and test execution date can diverge.
- Records with missing or unparseable `test_date` are excluded from canonical/read-model tables by default.
- File download, media URL fetch, waveform parsing, and package parsing are outside Schema v1.0.

## Layer Contract

- Raw/provenance layer is the source of truth.
- `source_payloads` is immutable by endpoint/canonical URL/payload hash.
- `source_payload_observations` stores repeated observations of the same immutable payload.
- `canonical_row_sources` connects every canonical/read-model row back to raw source payload rows.
- Canonical tables are normalized, rebuildable entities derived from raw payloads.
- Read models and facets are rebuildable derivatives for API/filter performance.

## Canonical Entity Decisions

- `occupants` are normalized occupant slots, not raw source observations.
- `restraints` are occupant-context restraint assignments and must preserve occupant/subject context.
- `barriers` are semantic-deduped across `metadata_export` and `barrier_info` when they describe the same barrier.
- `instrumentation_channels` are canonicalized by `test_id + curve_no`.
- `media_assets` is a URL/metadata registry only. No files are downloaded.
- Empty `intrusion_info`, `barrier_info`, or `occupant_info` payloads remain successful source payloads when the endpoint returns a successful empty result.
- Data packages use `asset_kind=data_package` plus `asset_subtype`; package contents are not parsed.
- `code_values` is a derived dictionary registry, not source of truth.

## Evidence From 1000-Test Hardening Baseline

Endpoint completeness after 1000-test backfill:

| Endpoint | Expected | Actual | Missing |
|---|---:|---:|---:|
| `intrusion_info` | 1013 | 1013 | 0 |
| `restraint_info` | 1168 | 1168 | 0 |
| `instrumentation_info` | 5400 | 5400 | 0 |

Schema hardening results:

| Metric | Before | After |
|---|---:|---:|
| mapped fields | 10 | 36 |
| unmapped fields | 287 | 274 |
| dictionary candidates | 137 | 81 |
| test_classification unknown | 105 | 0 |

Additional 1000-test hardening facts:

- identifier no-action fields: 19
- numeric measurement column candidates: 7
- P0/P1/P2/P3: 0/0/241/19
- source_conflicts P0/P1: 0/0
- required facet coverage: 26/27
- missing facet `dummy_type`: accepted warning

## Evidence From 1500-Test Actual-Crash Expansion

The current cumulative DB includes the previous 1000-test pilot plus 500 additional actual-crash tests.

| Metric | Count |
|---|---:|
| canonical tests | 1500 |
| source_payloads | 25676 |
| source_payload_observations | 25676 |
| instrumentation_channels | 186763 |
| media_assets | 100632 |
| code_values | 727 |

Endpoint completeness after 1500-test actual-crash expansion:

| Endpoint | Expected | Actual | Missing |
|---|---:|---:|---:|
| `intrusion_info` | 1535 | 1535 | 0 |
| `restraint_info` | 2010 | 2010 | 0 |
| `instrumentation_info` | 10131 | 10131 | 0 |

Audit result:

- scope violations: 0
- read-model out-of-scope rows: 0
- duplicate groups for vehicles, test_participants, barriers, occupants, restraints, instrumentation_channels, media_assets: 0
- semantic hard failures: 0
- data package unclassified candidates: 0
- restraint_info missing requests: 0

## P0/P1 Blocker Decision

P0/P1 blockers are 0 in the 1000-test hardening baseline and remain 0 in the 1500-test local analysis.

Remaining recommendations are P2/P3 only. These are handled as schema governance backlog, not full-scale blockers.

## P2/P3 Backlog Decision

Apply before full-scale:

- code_values rebuild CLI and derived dictionary registry policy
- backlog triage CLI and deterministic classification rules
- dummy_type accepted-warning policy
- conflict taxonomy policy
- no payload_json/raw_row_json whole-column index policy

Accept for v1.0 without schema change:

- numeric measurement fields remain canonical numeric columns or raw-only until a specific analysis use case exists
- broad index candidates are documented, not all applied to SQLite before full-scale
- existing 26/27 facet coverage is accepted with `dummy_type` warning

Defer post full-scale:

- high-cardinality sensor attachment cleanup
- detailed injury/intrusion measurement promotion beyond current canonical model
- PostgreSQL-specific index tuning

Requires manual domain review:

- non-required low-cardinality fields that may be domain labels but are not in the v1.0 allowed dictionary list
- ambiguous metadata_export instrumentation/photo/video row identifiers

Raw-only no action:

- identifiers such as `testNo`, `vehicleNo`, `curveNo`, row ids
- URL/hash/path fields
- package contents and file internals

## Full-Scale Approval Gate

Before full-scale execution, owner approval is still required for:

- final manifest-only dry run
- rate limit and retry parameters
- database backup path
- maximum runtime and stop conditions
- whether to run an optional 250-test bounded validation before full-scale

Full-scale execution remains blocked without separate approval.

## Validation

- `schema rebuild-code-values` completed against the local 1500-test DB with 17 code sets and 727 values.
- `schema optimize-analyze` completed against the local 1500-test DB.
- `schema backlog-triage` completed and reported `full_scale_blocked=false`.
- Live manifest safety negative passed: missing `--allow-live` failed and created no output.
- Live manifest env safety negative passed: missing `NHTSA_METADATA_ALLOW_LIVE=true` failed and created no output.
- Live backfill safety negative passed: missing live authorization failed and created no output.
- `pytest -q`: 97 passed.
- `ruff check src tests`: passed.
- `mypy src\nhtsa_metadata`: passed.
- `scripts\verify.ps1`: passed.
- `.harness\run.ps1`: passed.
