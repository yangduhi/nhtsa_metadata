# Full-Scale Schema Optimization 2011+

## Scope
- Based on the 3891-row Stage D metadata-only SQLite DB.
- 2011+ only.
- no full crawler.
- no file download.
- no waveform/package parsing.

## Input DB Summary
- tests: 3891
- source_field_catalog: 521
- source_payloads: 66318
- source_payload_sections: 101337
- source_payload_observations: 66318
- canonical_row_sources: 1378515
- source_conflicts: 9447
- tests: 3891
- vehicles: 4693
- test_participants: 6320
- barriers: 1627
- occupants: 5875
- restraints: 12522
- instrumentation_channels: 470435
- instrumentation_channel_details: 0
- injury_metrics: 39326
- deformation_measurements: 46930
- intrusion_measurements: 0
- media_assets: 289821
- test_filter_summary: 3891
- test_facets: 1296
- asset_summary: 13718
- code_values: 0
- test_classification: 3891
- field_coverage_snapshots: 0

## Field Coverage Summary
- field profiles: 311
- mapped fields: 37
- unmapped fields: 274
- extra_json fields: 0
- wildcard path normalization example: `$.results[*].axisDirofSensor` style paths are expected when array indexes appear.

## Top Repeated Unmapped Field Paths
- `occupant_info` `$.results[*].millisecCliptDoraxRegionPeakAcceleration` support=3891 non_null=0.95
- `occupant_info` `$.results[*].chestSeverityIndex` support=3891 non_null=0.92
- `vehicle_info` `$.results[*].vehicleWidth` support=3891 non_null=0.87
- `vehicle_info` `$.results[*].vehicleLength` support=3891 non_null=0.87
- `vehicle_info` `$.results[*].vaxCrushDistance` support=3891 non_null=0.83
- `occupant_info` `$.results[*].leftFemurPeakLoadMeasure` support=3891 non_null=0.75
- `occupant_info` `$.results[*].rightFemurPeakLoadMeasure` support=3891 non_null=0.75
- `occupant_info` `$.results[*].shoulderBeltPeakLoadMeasurement` support=3891 non_null=0.71
- `occupant_info` `$.results[*].lapBeltPeakLoadMeasurement` support=3891 non_null=0.70
- `metadata_export` `$.results[*].OCCUPANT[*].CLIP3M` support=3891 non_null=0.95

## Recommendation Summary
- P0/P1/P2/P3: 0/0/117/19
- column candidates: 0
- dictionary candidates: 0
- code values candidates: 0
- populated code value rows: 0
- facet candidates: 0
- index candidates: 0
- alias map candidates: 0
- semantic key candidates: 0
- identifier no-action fields: 19
- numeric measurement column candidates: 0

## Source Conflict Taxonomy
- total conflicts: 9447
- P0/P1/P2/P3: 0/0/0/9447
- by class: {'benign_alias_difference': 3412, 'numeric_rounding_difference': 6035}

## Data Package Invariant
- candidate assets: 19217
- classified assets: 19222
- classified non-candidate assets: 5
- candidate unclassified count: 0
- status: pass

## Test Facet Coverage
- required facets: 27
- present facets: 26
- missing facets: ['dummy_type']

## Proposed Schema Optimization Backlog
- P2 requires_manual_review: occupant_info $.results[*].millisecCliptDoraxRegionPeakAcceleration (type instability needs manual review)
- P2 requires_manual_review: occupant_info $.results[*].chestSeverityIndex (type instability needs manual review)
- P2 requires_manual_review: vehicle_info $.results[*].vehicleWidth (type instability needs manual review)
- P2 requires_manual_review: vehicle_info $.results[*].vehicleLength (type instability needs manual review)
- P2 requires_manual_review: vehicle_info $.results[*].vaxCrushDistance (type instability needs manual review)
- P2 requires_manual_review: occupant_info $.results[*].leftFemurPeakLoadMeasure (type instability needs manual review)
- P2 requires_manual_review: occupant_info $.results[*].rightFemurPeakLoadMeasure (type instability needs manual review)
- P2 requires_manual_review: occupant_info $.results[*].shoulderBeltPeakLoadMeasurement (type instability needs manual review)
- P2 requires_manual_review: occupant_info $.results[*].lapBeltPeakLoadMeasurement (type instability needs manual review)
- P2 requires_manual_review: metadata_export $.results[*].OCCUPANT[*].CLIP3M (type instability needs manual review)
- P2 requires_manual_review: test_detail $.results[*].impactAngle (type instability needs manual review)
- P2 requires_manual_review: test_summary $.results[*].impactAngle (type instability needs manual review)
- P2 requires_manual_review: metadata_export $.results[*].VEHICLE[*].PDOF (type instability needs manual review)
- P2 requires_manual_review: metadata_export $.results[*].VEHICLE[*].CRBANG (type instability needs manual review)
- P2 requires_manual_review: metadata_export $.results[*].OCCUPANT[*].PELVG (type instability needs manual review)
- P2 requires_manual_review: metadata_export $.results[*].OCCUPANT[*].CSI (type instability needs manual review)
- P2 requires_manual_review: metadata_export $.results[*].OCCUPANT[*].TTI (type instability needs manual review)
- P2 requires_manual_review: test_detail $.results[*].typeofRecorder (type instability needs manual review)
- P2 requires_manual_review: metadata_export $.results[*].OCCUPANT[*].CNTRH1D (type instability needs manual review)
- P2 requires_manual_review: metadata_export $.results[*].OCCUPANT[*].CNTRH2D (type instability needs manual review)

## Do Not Change Yet
- raw-only no-action candidates: 194
- high variability fields, low support fields, ambiguous commentary fields, and file/data package internals remain raw-only.

## Decision
- The 1000-test pilot schema is acceptable for 250-test planning.
