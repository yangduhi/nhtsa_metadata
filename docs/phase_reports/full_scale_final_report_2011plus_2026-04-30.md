# Full-Scale Final Report 2011+

## Executive Conclusion
- Stage D metadata-only collection: completed.
- Stage E endpoint/schema/code_values/smoke: completed.
- v1.4 classification: hard fail on full 3891-row corpus; do not broaden rules automatically.
- Stage D data collection itself is complete and reproducible from the approved authoritative manifest.

## Approval and Scope
- owner approval: granted in current thread.
- discovery authority: reference_seeded_live_validated.
- manifest: data/full_2011plus_authoritative_manifest.csv
- manifest_hash: b4a1262938d33793bff0d4aca78222e4bab51c7253d4084fbb80597096abe6be
- scope: test_date >= 2011-01-01.
- file/media/package download: not performed.
- waveform/TDMS/UDS/EV/ABF/ISO/ZIP/package parsing: not performed.

## Manifest
- rows: 3891
- date_range: 2011-01-03 to 2025-09-25
- duplicate_test_no: 0
- pre_2011_rows: 0
- missing_or_parse_failed_date: 0
- anchors 7201/10001/10003: present/present/present
- authority_distribution: live_by_search=3260, live_year_slice_by_search=608, reference_seed_live_validated=23

## Runtime Summary
- DB path: data/full_2011plus_metadata_only_stage_d_2026-04-30.sqlite
- DB size bytes: 2641743872
- request_delay_seconds: 0.2
- collection_run_items: {'skipped_existing': 4254, 'succeeded': 7937}

| run_id | status | started_at | finished_at |
|---:|---|---|---|
| 1 | interrupted | 2026-04-30 12:15:49.925249 | 2026-04-30 13:51:36.952840 |
| 2 | interrupted | 2026-04-30 13:51:36.975057 | 2026-05-01 11:47:15.665257 |
| 3 | interrupted | 2026-05-01 11:47:15.673769 | 2026-05-02 04:18:02.923460 |
| 4 | succeeded | 2026-05-02 04:18:02.936479 | 2026-05-02 07:53:07.880416 |
| 5 | succeeded | 2026-05-02 07:59:17.249915 | 2026-05-02 08:31:31.832264 |

## Endpoint Summary
- expected_tests: 3891
- collected_tests: 3891
- missing_tests: 0
- missing_endpoint_matrix_count: 0
- source_payloads: 66318
- source_payload_observations: 66318
- empty_successful_payloads: 6678

## Schema Audit Summary
- schema_contract_hard_failures: 0
- schema_contract_warnings: 1
- endpoint_matrix_hard_failures: 0
- endpoint_matrix_warnings: 0
- semantic_hard_failures: 0
- duplicate canonical groups: 0 across audited canonical tables
- source_conflicts P0/P1/P2/P3: 0/0/0/9447
- P0/P1 schema recommendations: 0/0

## code_values Rebuild
- code_sets: 17
- inserted rows: 757

## v1.4 Classification Summary
- total: 3891
- classified: 3844
- unclassified: 47
- classification_rate: 0.987921
- known_false_positive_count: 26
- live_api_used: false
- alias_used: 606
- fallback_used: 852
- generic_used: 572
- aggregate_used: 195
- metadata_gap_used: 666

## Classification Hard Fail Issue List
- unclassified_count > 0: 47 rows.
- known_false_positive_count > 0: 26 rows.
- Rule body was not broadened during Stage E; v1.4 full-scale issue list is preserved for targeted v1.4.1/v1.5 analysis.

| check | count | samples |
|---|---:|---|
| NCAP static airbag/OOP classified as pedestrian aggregate | 0 | `[]` |
| pedestrian calibration/certification classified as pedestrian aggregate | 0 | `[]` |
| explicit-213B-missing child restraint sled has 213B candidate | 0 | `[]` |
| side pole over-confirmed without program keyword | 8 | `[10841, 10842, 10845, 11600, 11604, 14354, 14355, 14604]` |
| 48 km/h frontal fixed barrier over-confirmed without standard keyword | 0 | `[]` |
| oblique RMDB/OMDB classified as current FMVSS/NCAP core | 0 | `[]` |
| ADAS/crash avoidance classified as crashworthiness | 0 | `[]` |
| ejection mitigation classified as vehicle crash | 0 | `[]` |
| roof crush classified as dynamic rollover | 0 | `[]` |
| sled test classified as full vehicle crash | 18 | `[9230, 9231, 9232, 9233, 9234, 9235, 9236, 9237, 9238, 9239]` |
| Part 581 classified as FMVSS 208/214/301 | 0 | `[]` |

## Top Canonical Rules

| count | canonical_rule_id |
|---:|---|
| 48 | `ECE_R16_OCCUPANT_RESTRAINT_SLED_WITH_VEHICLE_BODY` |
| 66 | `FMVSS_208_FRONTAL_RIGID_BARRIER_48_OR_56KPH_DUMMY_UNKNOWN` |
| 22 | `FMVSS_208_FRONTAL_RIGID_BARRIER_UNBELTED_ANGLE_UP_TO_30_48KPH_LEGACY_OR_OPTION` |
| 261 | `FMVSS_208_LOW_RISK_DEPLOYMENT_OOP_GENERIC` |
| 74 | `FMVSS_213_CHILD_RESTRAINT_FRONTAL_SLED_CONFIG_II_32KPH` |
| 261 | `FMVSS_213_CHILD_RESTRAINT_FRONTAL_SLED_CONFIG_I_48KPH` |
| 5 | `FMVSS_213_CHILD_RESTRAINT_RESEARCH_OR_NON_NOMINAL_SLED` |
| 50 | `FMVSS_214_SIDE_POLE_20MPH_75DEG_254MM` |
| 76 | `FMVSS_226_EJECTION_MITIGATION_GENERIC` |
| 10 | `FMVSS_301_FUEL_REAR_MDB_80KPH_70PERCENT_OVERLAP` |
| 2 | `FMVSS_301_FUEL_SYSTEM_INTEGRITY_SLED_SIMULATION` |
| 14 | `FMVSS_301_REAR_MDB_COMPLIANCE_SPEED_MISSING_OR_301R_GENERIC` |
| 6 | `GENERIC_FRONT_FIXED_BARRIER_30MPH` |
| 26 | `GENERIC_FRONT_FIXED_BARRIER_35MPH` |
| 10 | `GENERIC_SIDE_MDB_33_5MPH` |

## Stop Conditions
- file/media/package download: not encountered.
- modelYear/test_no range scoping: not used.
- source payload persistence failure: 0 observed.
- endpoint completeness hard fail: none.
- classification acceptance: failed due 47 unclassified and 26 known false-positive rows.

## Recommended Next Actions
1. Create a targeted v1.4.1 issue analysis for the 47 unclassified rows.
2. Fix the 8 side-pole over-confirmed rows by requiring stronger NCAP evidence or routing generic FMVSS pole text to FMVSS/research review.
3. Fix the 18 sled-with-body oblique rows by preventing full-vehicle oblique rules from outranking sled-specific rules when test_configuration is SLED WITH VEHICLE BODY.
