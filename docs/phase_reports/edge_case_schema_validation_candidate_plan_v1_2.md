# Edge-Case Schema Validation Candidate Plan v1.2

## Scope
- Candidate manifest only; no collect approval is implied.
- Selected from authoritative manifest rows not present in the 1500 DB.
- Limit: <= 100.

## Summary
- candidate rows: 100
- candidate file: data\edge_case_schema_validation_candidate_manifest_v1_2.csv

## Priority Rules
- 2022-2025 validated supplement rows first.
- rare configuration/test type/classification next.
- UNKNOWN/manual-risk proxy strata next.

## Samples
- 15378 2023-10-02 reference_seed_live_validated VEHICLE INTO POLE
- 15389 2023-09-14 reference_seed_live_validated IMPACTOR INTO VEHICLE
- 15395 2023-10-16 reference_seed_live_validated VEHICLE INTO POLE
- 15396 2023-10-09 reference_seed_live_validated VEHICLE INTO POLE
- 15488 2023-11-03 reference_seed_live_validated VEHICLE INTO BARRIER
- 15492 2023-12-18 reference_seed_live_validated VEHICLE INTO BARRIER
- 15493 2023-12-08 reference_seed_live_validated VEHICLE INTO BARRIER
- 15504 2024-12-17 reference_seed_live_validated VEHICLE INTO BARRIER
- 15513 2025-09-25 reference_seed_live_validated IMPACTOR INTO VEHICLE
- 14243 2022-08-24 live_year_slice_by_search VEHICLE INTO BARRIER
- 14246 2022-08-25 live_year_slice_by_search IMPACTOR INTO VEHICLE
- 14248 2022-08-29 live_year_slice_by_search VEHICLE INTO BARRIER
- 14251 2022-10-13 live_year_slice_by_search IMPACTOR INTO VEHICLE
- 14252 2022-10-14 live_year_slice_by_search VEHICLE INTO BARRIER
- 14253 2022-10-27 live_year_slice_by_search IMPACTOR INTO VEHICLE
- 14255 2022-11-02 live_year_slice_by_search IMPACTOR INTO VEHICLE
- 14256 2022-11-03 live_year_slice_by_search VEHICLE INTO POLE
- 14257 2022-11-04 live_year_slice_by_search VEHICLE INTO BARRIER
- 14258 2022-11-16 live_year_slice_by_search VEHICLE INTO BARRIER
- 14259 2022-09-27 live_year_slice_by_search IMPACTOR INTO VEHICLE
- 14260 2022-11-18 live_year_slice_by_search VEHICLE INTO POLE
- 14261 2022-11-17 live_year_slice_by_search IMPACTOR INTO VEHICLE
- 14262 2022-11-23 live_year_slice_by_search VEHICLE INTO BARRIER
- 14263 2022-09-21 live_year_slice_by_search IMPACTOR INTO VEHICLE
- 14266 2022-12-06 live_year_slice_by_search VEHICLE INTO BARRIER

## Decision
- Optional edge-case bounded validation requires separate approval.
