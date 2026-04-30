# 1000-Test 2011+ Schema Optimization Report

## Scope
- Based on the 1000-test bounded live pilot DB.
- 2011+ only.
- no full crawler.
- no file download.
- no waveform/package parsing.

## Input DB Summary
- tests: 1000
- source_field_catalog: 497
- source_payloads: 14570
- source_payload_sections: 23570
- source_payload_observations: 14570
- canonical_row_sources: 275760
- source_conflicts: 2233
- tests: 1000
- vehicles: 1107
- test_participants: 1421
- barriers: 314
- occupants: 1277
- restraints: 2191
- instrumentation_channels: 97823
- instrumentation_channel_details: 0
- injury_metrics: 8176
- deformation_measurements: 11070
- intrusion_measurements: 0
- media_assets: 48462
- test_filter_summary: 1000
- test_facets: 297
- asset_summary: 3116
- code_values: 0
- test_classification: 1000
- field_coverage_snapshots: 0

## Field Coverage Summary
- field profiles: 297
- mapped fields: 10
- unmapped fields: 287
- extra_json fields: 0
- wildcard path normalization example: `$.results[*].axisDirofSensor` style paths are expected when array indexes appear.

## Top Repeated Unmapped Field Paths
- `instrumentation_info` `$.results[*].axisDirofSensor` support=1000 non_null=1.00
- `instrumentation_info` `$.results[*].curveNo` support=1000 non_null=1.00
- `instrumentation_info` `$.results[*].dataMeasurementUnits` support=1000 non_null=1.00
- `instrumentation_info` `$.results[*].dataStatus` support=1000 non_null=1.00
- `instrumentation_info` `$.results[*].instrumentationCommentary` support=1000 non_null=1.00
- `instrumentation_info` `$.results[*].numberofFirstPoint` support=1000 non_null=1.00
- `instrumentation_info` `$.results[*].numberofLastPoint` support=1000 non_null=1.00
- `instrumentation_info` `$.results[*].sensorAttachment` support=1000 non_null=1.00
- `instrumentation_info` `$.results[*].sensorType` support=1000 non_null=1.00
- `instrumentation_info` `$.results[*].testNo` support=1000 non_null=1.00

## Recommendation Summary
- P0/P1/P2/P3: 0/0/300/0
- column candidates: 1
- dictionary candidates: 137
- facet candidates: 0
- index candidates: 16
- alias map candidates: 0
- semantic key candidates: 0

## Proposed Schema Optimization Backlog
- P2 dictionary_candidate: instrumentation_info $.results[*].axisDirofSensor (stable low-cardinality repeated field)
- P2 dictionary_candidate: instrumentation_info $.results[*].curveNo (stable low-cardinality repeated field)
- P2 dictionary_candidate: instrumentation_info $.results[*].dataMeasurementUnits (stable low-cardinality repeated field)
- P2 dictionary_candidate: instrumentation_info $.results[*].dataStatus (stable low-cardinality repeated field)
- P2 dictionary_candidate: instrumentation_info $.results[*].instrumentationCommentary (stable low-cardinality repeated field)
- P2 dictionary_candidate: instrumentation_info $.results[*].numberofFirstPoint (stable low-cardinality repeated field)
- P2 dictionary_candidate: instrumentation_info $.results[*].numberofLastPoint (stable low-cardinality repeated field)
- P2 dictionary_candidate: instrumentation_info $.results[*].sensorAttachment (stable low-cardinality repeated field)
- P2 dictionary_candidate: instrumentation_info $.results[*].sensorType (stable low-cardinality repeated field)
- P2 dictionary_candidate: instrumentation_info $.results[*].testNo (stable low-cardinality repeated field)
- P2 dictionary_candidate: instrumentation_info $.results[*].timeIncrement (stable low-cardinality repeated field)
- P2 dictionary_candidate: restraint_info $.results[*].vehicleNo (stable low-cardinality repeated field)
- P2 dictionary_candidate: instrumentation_info $.results[*].channelStatus (stable low-cardinality repeated field)
- P2 dictionary_candidate: occupant_info $.results[*].vehicleNo (stable low-cardinality repeated field)
- P2 dictionary_candidate: restraint_info $.results[*].testNo (stable low-cardinality repeated field)
- P2 dictionary_candidate: vehicle_info $.results[*].vehicleNo (stable low-cardinality repeated field)
- P2 dictionary_candidate: instrumentation_info $.results[*].vehicleNo (stable low-cardinality repeated field)
- P2 dictionary_candidate: occupant_info $.results[*].occupantLocation (stable low-cardinality repeated field)
- P2 dictionary_candidate: occupant_info $.results[*].occupantType (stable low-cardinality repeated field)
- P2 dictionary_candidate: occupant_info $.results[*].restraintInformation (stable low-cardinality repeated field)

## Do Not Change Yet
- raw-only no-action candidates: 13
- high variability fields, low support fields, ambiguous commentary fields, and file/data package internals remain raw-only.

## Decision
- The 1000-test pilot schema is acceptable for 250-test planning.
