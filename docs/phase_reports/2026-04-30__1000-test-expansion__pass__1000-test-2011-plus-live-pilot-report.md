# 2026-04-30 | 1000-test expansion | PASS | 1000-Test 2011+ Live Pilot Report

## Conclusion
- Result: passed with documented resume condition.
- 250+ or full-crawler execution: not performed.
- File download/media fetch/package parsing: not performed.
- Schema optimization: completed; P0 recommendations = 0.

## Execution Scope
- Live manifest build: yes.
- Live collect: yes, bounded to the 1000-row manifest.
- Manifest path: `data/stratified_live_pilot_2011plus_1000_manifest.csv`
- Database path: `data/stratified_live_pilot_2011plus_1000.sqlite`
- Audit path: `data/schema_audit_report_2011plus_1000.json`
- Schema optimization JSON: `data/schema_optimization_report_2011plus_1000.json`
- Schema optimization Markdown: `docs/phase_reports/2026-04-30__1000-test-expansion__recorded__1000-test-2011-plus-schema-optimization-report.md`

## Manifest
- Rows: 1000
- Date range: 2011-01-03 to 2025-09-23
- Anchors: 7201=True, 10001=True, 10003=True
- Duplicate test_no: 0
- Pre-2011 rows: 0
- Missing test_date: 0
- Balance status: {'relaxed_missing_year': 1000}
- Candidate vs live overlap: 667 / 1000

## Collection
- Collection runs: 2
- Collection run statuses: [('started', 1), ('succeeded', 1)]
- Collection run items: 1389
- Collection item statuses: [('skipped_existing', 389), ('succeeded', 1000)]
- Note: one earlier long-running collect process was interrupted by the tool timeout after partial progress. The second run resumed safely; existing tests were skipped and the final canonical/read-model set is 1000 tests.
- Source payloads: 14570
- Source payload observations: 14570
- Source field catalog rows: 497

## Endpoint Coverage
- barrier_info: 1000
- instrumentation_info: 5400
- intrusion_info: 2
- metadata_export: 1000
- multimedia_files: 1000
- occupant_info: 1000
- restraint_info: 1168
- test_detail: 1000
- test_summary: 1000
- vehicle_documents: 1000
- vehicle_info: 1000

## Canonical And Read Model
- tests: 1000
- test_filter_summary: 1000
- vehicles: 1107
- test_participants: 1421
- barriers: 314
- occupants: 1277
- restraints: 2191
- instrumentation_channels: 97823
- media_assets: 48462
- canonical_row_sources: 275760

## Audit
- Scope violations: 0
- Read-model out-of-scope rows: 0
- Duplicate groups: {'barriers': 0, 'instrumentation_channels': 0, 'media_assets': 0, 'occupants': 0, 'restraints': 0, 'test_participants': 0, 'vehicles': 0}
- Semantic hard failures: 0
- Data package candidates: 4960
- Classified data packages: 4963
- Unclassified asset candidates: 0
- Restraint info expected/actual/missing: 1168/1168/0
- Unmapped field count: 480
- Wildcard path example: `$.results[*].axisDirofSensor`

## Baseline
### 10001
- vehicles: 1
- participants: ['barrier:1', 'subject_vehicle:1']
- barriers: 1
- occupants: 2
- restraints: 6
- instrumentation_channels: 634
- media_assets: 105
- barrier semantic status: fixed

### 10003
- vehicles: 2
- participants: ['impactor_vehicle:1', 'subject_vehicle:1']
- barriers: 0
- occupants: 2
- restraints: 6
- instrumentation_channels: 63
- media_assets: 152
- participant audit: [{'count': 1, 'participant_kind': 'impactor_vehicle'}, {'count': 1, 'participant_kind': 'subject_vehicle'}]

### 7201
- canonical exists: yes
- test_date: 2011-01-03
- scope_status: in_scope
- vehicles: 1
- occupants: 2
- instrumentation_channels: 227

## Test Classification Distribution
- frontal:classified: 584
- frontal_barrier:classified: 123
- unknown:needs_review: 105
- side:classified: 94
- side_impactor:classified: 86
- rear:classified: 8

## Schema Optimization
- Field profiles: 297
- Mapped/unmapped/extra_json: 10/287/0
- Recommendation priorities P0/P1/P2/P3: 0/0/300/0
- Column candidates: 1
- Dictionary candidates: 137
- Facet candidates: 0
- Index candidates: 16
- Semantic key candidates: 0
- Raw-only no-action items: 13

## Top Schema Recommendations
- P2 dictionary_candidate: `instrumentation_info $.results[*].axisDirofSensor` - stable low-cardinality repeated field
- P2 dictionary_candidate: `instrumentation_info $.results[*].curveNo` - stable low-cardinality repeated field
- P2 dictionary_candidate: `instrumentation_info $.results[*].dataMeasurementUnits` - stable low-cardinality repeated field
- P2 dictionary_candidate: `instrumentation_info $.results[*].dataStatus` - stable low-cardinality repeated field
- P2 dictionary_candidate: `instrumentation_info $.results[*].instrumentationCommentary` - stable low-cardinality repeated field
- P2 dictionary_candidate: `instrumentation_info $.results[*].numberofFirstPoint` - stable low-cardinality repeated field
- P2 dictionary_candidate: `instrumentation_info $.results[*].numberofLastPoint` - stable low-cardinality repeated field
- P2 dictionary_candidate: `instrumentation_info $.results[*].sensorAttachment` - stable low-cardinality repeated field
- P2 dictionary_candidate: `instrumentation_info $.results[*].sensorType` - stable low-cardinality repeated field
- P2 dictionary_candidate: `instrumentation_info $.results[*].testNo` - stable low-cardinality repeated field

## Safety
- Live safety remains gated by `--source live`, `--allow-live`, and `NHTSA_METADATA_ALLOW_LIVE=true`.
- Default verify/harness remains fixture/mock only.
- Data artifacts remain under ignored `data/` paths.

## Decision
- 1000-test bounded pilot passed the hard data gates.
- Schema optimizer found no P0 recommendations; next larger planning can be considered only after reviewing P2 dictionary/index backlog.
- Full crawler remains out of scope.
