# Full-Scale Schema Capacity Estimate

## Summary
- estimated_full_tests: 3260
- baseline_db_tests: 1500
- scale_factor: 2.1733
- estimated_endpoint_requests: 55802
- estimated_sqlite_db_size_bytes: 2185826140
- sqlite_recommendation: sqlite_possible_for_full_scale_metadata_only

## Estimated Table Counts
- asset_summary: 10962
- barriers: 1339
- canonical_row_sources: 1149606
- code_values: 1580
- collection_run_items: 7437
- collection_runs: 11
- deformation_measurements: 38207
- field_coverage_snapshots: 0
- injury_metrics: 30579
- instrumentation_channel_details: 0
- instrumentation_channels: 405898
- intrusion_measurements: 1878
- media_assets: 218707
- occupants: 4612
- restraints: 9528
- source_conflicts: 7533
- source_endpoints: 0
- source_field_catalog: 1111
- source_payload_observations: 55803
- source_payload_sections: 85143
- source_payloads: 55803
- test_classification: 3260
- test_facets: 2538
- test_filter_summary: 3260
- test_participants: 5159
- tests: 3260
- vehicles: 3821

## Runtime By Delay
- delay=0.1s: request delay 1.55 hours
- delay=0.25s: request delay 3.88 hours
- delay=0.5s: request delay 7.75 hours
- delay=1.0s: request delay 15.5 hours

## Bottleneck Tables
- canonical_row_sources: 1149606
