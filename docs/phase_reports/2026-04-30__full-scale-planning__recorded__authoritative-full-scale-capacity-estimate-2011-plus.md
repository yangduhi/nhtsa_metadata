# 2026-04-30 | Full-scale planning | RECORDED | Authoritative Full-Scale Capacity Estimate 2011+

## Scope
- Based on `data/full_2011plus_authoritative_manifest.csv`.
- Metadata endpoint capacity estimate only.
- No full crawler, no detail collect, no file download.

## New Authoritative Estimate
- baseline_db_tests: 1500
- estimated_full_tests: 3891
- scale_factor: 2.594
- estimated_endpoint_requests: 66604
- estimated_sqlite_db_size_bytes: 2609049018
- sqlite_recommendation: sqlite_possible_for_full_scale_metadata_only

## Comparison With v1.1 Live-Only Estimate
- estimated_full_tests: old=3260 new=3891
- estimated_endpoint_requests: old=55802 new=66604
- estimated_sqlite_db_size_bytes: old=2185826140 new=2609049018
- sqlite_recommendation: old=sqlite_possible_for_full_scale_metadata_only new=sqlite_possible_for_full_scale_metadata_only

## Endpoint Request Estimate
- barrier_info: 3891
- instrumentation_info: 26280
- intrusion_info: 3982
- metadata_export: 3891
- multimedia_files: 3891
- occupant_info: 3891
- restraint_info: 5214
- test_detail: 3891
- test_summary: 3891
- vehicle_documents: 3891
- vehicle_info: 3891

## Bottleneck Tables
- canonical_row_sources: 1372122

## Runtime Estimates
- delay=0.1s: request delay 1.85 hours
- delay=0.2s: request delay 3.7 hours
- delay=0.5s: request delay 9.25 hours
- delay=1.0s: request delay 18.5 hours

## Operational Requirement
- Use resumable collection runs.
- Back up DB before Stage D.
- Keep `data/` artifacts ignored.
- Stage D full-scale collect still requires separate owner approval.
