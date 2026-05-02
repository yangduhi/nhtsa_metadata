# Schema Contract Validation 2011+

## Scope
- DB schema v1.1 full-cover readiness validation.
- Read-only validation; no live API, no detail collect, no file download.

## Result
- result: pass
- hard failures: 0
- warnings: 1

## Required Tables
- collection_runs: db=True model=True
- collection_run_items: db=True model=True
- source_endpoints: db=True model=True
- source_payloads: db=True model=True
- source_payload_observations: db=True model=True
- source_payload_sections: db=True model=True
- source_field_catalog: db=True model=True
- source_conflicts: db=True model=True
- canonical_row_sources: db=True model=True
- discovery_runs: db=True model=True
- discovery_manifest_rows: db=True model=True
- discovery_authority_decisions: db=True model=True
- tests: db=True model=True
- test_participants: db=True model=True
- vehicles: db=True model=True
- barriers: db=True model=True
- occupants: db=True model=True
- restraints: db=True model=True
- instrumentation_channels: db=True model=True
- instrumentation_channel_details: db=True model=True
- injury_metrics: db=True model=True
- deformation_measurements: db=True model=True
- intrusion_measurements: db=True model=True
- media_assets: db=True model=True
- code_values: db=True model=True
- test_filter_summary: db=True model=True
- test_classification: db=True model=True
- test_facets: db=True model=True
- asset_summary: db=True model=True
- field_coverage_snapshots: db=True model=True

## Lineage And Immutability
- source_payload immutability: True
- source_payload_observations link: True
- discovery provenance tables: pass

## Prohibited Index Policy
- result: pass
- whole-column `payload_json` / `raw_row_json` indexes are prohibited.

## Hard Failures
- none

## Warnings
- critical index not explicit: source_payload_observations('source_payload_id',)
