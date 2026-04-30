# Schema v1.0 Backlog Triage

## Scope

- Basis: local 1500-test actual-crash cumulative DB and schema optimization output.
- No live API call.
- No full crawler.
- No file download.
- JSON output: `data/schema_v1_0_backlog_triage.json` (ignored, not committed).

## Mandatory Rules

- P0/P1: full-scale blocked until resolved.
- P2 dictionary/index/facet: explicit v1.0 decision required.
- P3 documentation/cleanup: accepted or deferred, does not block.
- identifier_no_action: no schema change.
- numeric measurement fields: not dictionary candidates.
- file/data package internals: raw-only.

## Recommendation Counts

| Metric | Count |
|---|---:|
| total recommendations | 260 |
| P0 | 0 |
| P1 | 0 |
| P2 | 241 |
| P3 | 19 |
| code_values_candidate | 1 |
| dictionary_candidate | 82 |
| identifier_no_action | 19 |
| index_candidate | 17 |
| numeric_measurement_column_candidate | 7 |
| requires_manual_review | 134 |

## v1.0 Decision Counts

| Decision | Count |
|---|---:|
| apply_before_full_scale | 0 |
| accept_for_v1_0_no_change | 106 |
| defer_post_full_scale | 0 |
| requires_manual_domain_review | 135 |
| reject_false_positive | 0 |
| raw_only_no_action | 19 |

`apply_before_full_scale` is 0 for remaining recommendations because v1.0 finalization already applied the required governance change: `code_values` rebuild policy and CLI. Remaining P2/P3 items do not block full-scale approval review.

## Dictionary Candidate Policy

Allowed v1.0 dictionary/code systems:

- `sensor_type`
- `sensor_attachment`
- `sensor_axis`
- `data_measurement_unit`
- `data_status`
- `channel_status`
- `occupant_location`
- `occupant_type`
- `restraint_type`
- `restraint_deployment`
- `barrier_rigidity`
- `barrier_shape`
- `asset_kind`
- `asset_subtype`
- `test_configuration_key`
- `classification_status`
- `participant_kind`

Rejected as dictionary/code systems:

- `testNo`
- `vehicleNo`
- `curveNo`
- source row id
- URL/hash/path
- `numberofFirstPoint`
- `numberofLastPoint`
- `timeIncrement`
- speed/weight/length/width/HIC/load metric values

## Decision By Class

- `identifier_no_action`: raw-only no action.
- `numeric_measurement_column_candidate`: accept for v1.0 no change unless a measured analysis use case requires a column/facet later.
- `index_candidate`: accept for v1.0 no change; document in index plan and revisit after query measurements.
- `dictionary_candidate`: manual domain review unless it maps to an allowed code system.
- `code_values_candidate`: manual domain review when raw field name is ambiguous; canonical code_values registry already covers approved systems.
- `requires_manual_review`: manual domain review, not a full-scale blocker while P0/P1 remain zero.

## Full-Scale Readiness Impact

- P0/P1 are zero.
- `full_scale_blocked=false` in the generated triage JSON.
- Remaining P2/P3 backlog is accepted as governance backlog, not a blocker.
