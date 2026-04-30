# 1000-Test 2011+ Endpoint Completeness Report

## Scope
- Existing 1000-row 2011+ manifest only.
- No new test_no collection.
- No full crawler.
- No file download, media fetch, or package parsing.

## Policy
- `intrusion_info` expected target: all canonical vehicles in the manifest, except vehicles unambiguously classified only as `impactor_vehicle`.
- `restraint_info` expected target: distinct occupant requests observed from `occupant_info` payloads.
- `instrumentation_info` expected target: contiguous pages already scheduled for each manifest test.

## Pre-Backfill Coverage
| endpoint | expected | actual | missing | empty | non-empty |
|---|---:|---:|---:|---:|---:|
| test_summary | 1000 | 1000 | 0 | 0 | 1000 |
| metadata_export | 1000 | 1000 | 0 | 0 | 1000 |
| test_detail | 1000 | 1000 | 0 | 0 | 1000 |
| vehicle_info | 1000 | 1000 | 0 | 0 | 1000 |
| barrier_info | 1000 | 1000 | 0 | 686 | 314 |
| occupant_info | 1000 | 1000 | 0 | 185 | 815 |
| multimedia_files | 1000 | 1000 | 0 | 0 | 1000 |
| vehicle_documents | 1000 | 1000 | 0 | 0 | 1000 |
| intrusion_info | 1013 | 2 | 1011 | 2 | 0 |
| restraint_info | 1168 | 1168 | 0 | 118 | 1050 |
| instrumentation_info | 5400 | 5400 | 0 | 1 | 5399 |

## Backfill Execution
- Endpoint: intrusion_info
- Fetched: 1011
- Skipped existing: 2
- Failed: 0
- Source payloads before/after: 14570 / 15581
- No new test_no added: True
- Run id: 3

## After-Backfill Coverage
| endpoint | expected | actual | missing | empty | non-empty |
|---|---:|---:|---:|---:|---:|
| test_summary | 1000 | 1000 | 0 | 0 | 1000 |
| metadata_export | 1000 | 1000 | 0 | 0 | 1000 |
| test_detail | 1000 | 1000 | 0 | 0 | 1000 |
| vehicle_info | 1000 | 1000 | 0 | 0 | 1000 |
| barrier_info | 1000 | 1000 | 0 | 686 | 314 |
| occupant_info | 1000 | 1000 | 0 | 185 | 815 |
| multimedia_files | 1000 | 1000 | 0 | 0 | 1000 |
| vehicle_documents | 1000 | 1000 | 0 | 0 | 1000 |
| intrusion_info | 1013 | 1013 | 0 | 1011 | 2 |
| restraint_info | 1168 | 1168 | 0 | 118 | 1050 |
| instrumentation_info | 5400 | 5400 | 0 | 1 | 5399 |

## Canonical And Rebuild Impact
- canonical tests: 1000
- test_filter_summary: 1000
- source_payloads: 15581
- source_payload_observations: 15581
- intrusion_measurements: 48
- canonical_row_sources: 275808

## Remaining Exceptions
- `intrusion_info` has 1011 allowed empty responses. They are stored as source payloads and are not treated as failures.
- No endpoint has unexplained missing requests after backfill.
