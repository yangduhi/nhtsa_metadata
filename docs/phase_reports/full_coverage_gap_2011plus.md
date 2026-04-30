# Full Coverage Gap 2011+

## Scope
- Compares full 2011+ manifest-only universe against the 1500-test local DB.
- No detail collect, no file download, no package parsing.

## Summary
- full_manifest_tests: 3260
- db_tests: 1500
- overlap_tests: 1170
- full_manifest_only_tests: 2090
- db_only_tests: 330
- overlap_ratio_of_full: 0.3589
- edge_case_validation_needed: True

## Manifest Hard Gate
- row_count: 3260
- date_range: ['2011-01-03', '2021-12-02']
- duplicate_test_no: 0
- missing_or_parse_failed_date: 0
- pre_2011_rows: 0
- scope_status_values: ['in_scope']
- anchors: {7201: True, 10001: True, 10003: True}
- year_distribution: {2011: 345, 2012: 434, 2013: 470, 2014: 360, 2015: 249, 2016: 411, 2017: 321, 2018: 158, 2019: 184, 2020: 185, 2021: 143}
- test_type_distribution: {'CALIBRATION TEST': 9, 'EXPERIMENTAL NEW CAR ASSESSMENT TEST': 330, 'FMVSS 208 OCCUPANT CRASH PROTECTION': 327, 'FMVSS 213 CHILD RESTRAINT SYSTEMS': 266, 'FMVSS 214 SIDE IMPACT PROTECTION': 13, 'FMVSS 226 EJECTION MITIGATION': 76, 'FMVSS 301 FUEL SYSTEM INTEGRITY': 18, 'FMVSS COMPLIANCE TEST - UNSPECIFIED': 7, 'MODIFIED VEHICLE TEST': 25, 'NEW CAR ASSESSMENT TEST': 1061, 'OCCUPANT PERFORMANCE TEST': 181, 'OPTIONAL NEW CAR ASSESSMENT TEST': 346, 'OTHER': 91, 'OUT OF POSITION (TWG) SIDE AIRBAG DEPLOYMENT TESTS': 71, 'RESEARCH': 76, 'RESEARCH SAFETY VEHICLE TEST': 128, 'RMDB INTO FRONT 15 DEGREE STATIONARY VEHICLE, OVERLAP=35 PERCENT': 145, 'RMDB INTO FRONT 7 DEGREE STATIONARY VEHICLE, OVERLAP=20 PERCENT': 18, 'TEST PROCEDURE DEVELOPMENT': 55, 'VALIDATION NEW CAR ASSESSMENT TEST': 8, 'Validation New Car Assessment Test': 9}
- test_configuration_distribution: {'FORWARD COLLISION WARNING PERFORMANCE TEST': 45, 'IMPACTOR INTO IMPACTOR': 6, 'IMPACTOR INTO VEHICLE': 648, 'LANE DEPARTURE WARNING PERFORMANCE TEST': 31, 'LOW RISK DEPLOYMENT': 261, 'OTHER': 21, 'PEDESTRIAN': 195, 'ROLLOVER': 130, 'SLED WITH VEHICLE BODY': 126, 'SLED WITHOUT VEHICLE BODY': 446, 'STATIC AIR BAG TEST SIDE': 235, 'UNKNOWN': 76, 'VEHICLE INTO BARRIER': 571, 'VEHICLE INTO POLE': 457, 'VEHICLE INTO VEHICLE': 12}
- classification_distribution: {'airbag_static_or_low_risk': 496, 'frontal_barrier': 571, 'non_crash_adas': 76, 'pole': 457, 'rollover': 130, 'side_impactor': 648, 'sled': 572, 'unknown_or_other': 298, 'vehicle_to_vehicle': 12}

## Year Coverage
- 2011: full=345 db=93 status=represented
- 2012: full=434 db=92 status=represented
- 2013: full=470 db=176 status=represented
- 2014: full=360 db=92 status=represented
- 2015: full=249 db=92 status=represented
- 2016: full=411 db=108 status=represented
- 2017: full=321 db=165 status=represented
- 2018: full=158 db=90 status=represented
- 2019: full=184 db=90 status=represented
- 2020: full=185 db=90 status=represented
- 2021: full=143 db=90 status=represented
- 2022: full=0 db=89 status=db_only
- 2023: full=0 db=89 status=db_only
- 2024: full=0 db=89 status=db_only
- 2025: full=0 db=55 status=db_only

## Test Configuration Coverage
- FORWARD COLLISION WARNING PERFORMANCE TEST: full=45 db=45 status=represented
- IMPACTOR INTO IMPACTOR: full=6 db=6 status=represented
- IMPACTOR INTO VEHICLE: full=648 db=244 status=represented
- LANE DEPARTURE WARNING PERFORMANCE TEST: full=31 db=31 status=represented
- LOW RISK DEPLOYMENT: full=261 db=90 status=represented
- OTHER: full=21 db=21 status=represented
- PEDESTRIAN: full=195 db=90 status=represented
- ROLLOVER: full=130 db=130 status=represented
- SLED WITH VEHICLE BODY: full=126 db=90 status=represented
- SLED WITHOUT VEHICLE BODY: full=446 db=89 status=represented
- STATIC AIR BAG TEST SIDE: full=235 db=89 status=represented
- UNKNOWN: full=76 db=76 status=represented
- VEHICLE INTO BARRIER: full=571 db=245 status=represented
- VEHICLE INTO POLE: full=457 db=242 status=represented
- VEHICLE INTO VEHICLE: full=12 db=12 status=represented

## Classification Coverage
- airbag_static_or_low_risk: full=496 db=0 status=uncovered
- non_crash_adas: full=76 db=0 status=uncovered
- pole: full=457 db=0 status=uncovered
- sled: full=572 db=0 status=uncovered
- unknown_or_other: full=298 db=0 status=uncovered
- vehicle_to_vehicle: full=12 db=0 status=uncovered
- adas_fcw: full=0 db=45 status=db_only
- adas_ldw: full=0 db=31 status=db_only
- frontal: full=0 db=80 status=db_only
- frontal_barrier: full=571 db=231 status=represented
- low_risk_deployment: full=0 db=90 status=db_only
- pedestrian: full=0 db=99 status=db_only
- rear: full=0 db=12 status=db_only
- research_other: full=0 db=69 status=db_only
- rollover: full=130 db=130 status=represented
- side: full=0 db=237 status=db_only
- side_impactor: full=648 db=205 status=represented
- sled_with_body: full=0 db=90 status=db_only
- sled_without_body: full=0 db=89 status=db_only
- static_airbag: full=0 db=89 status=db_only

## Edge-Case Candidate Need
- decision: conditional: uncovered strata exist; edge-case bounded validation candidate prepared
- 11640 2017-05-25 SLED WITH VEHICLE BODY
- 11641 2017-05-31 SLED WITH VEHICLE BODY
- 11642 2017-06-01 SLED WITH VEHICLE BODY
- 11643 2017-06-05 SLED WITH VEHICLE BODY
- 11644 2017-06-06 SLED WITH VEHICLE BODY
- 11645 2017-06-07 SLED WITH VEHICLE BODY
- 11646 2017-06-07 SLED WITH VEHICLE BODY
- 11647 2017-06-08 SLED WITH VEHICLE BODY
- 11648 2017-06-09 SLED WITH VEHICLE BODY
- 10289 2017-07-24 SLED WITH VEHICLE BODY
- 10290 2017-07-25 SLED WITH VEHICLE BODY
- 10291 2017-07-25 SLED WITH VEHICLE BODY
- 10292 2017-07-26 SLED WITH VEHICLE BODY
- 10293 2017-07-27 SLED WITH VEHICLE BODY
- 10294 2017-07-27 SLED WITH VEHICLE BODY
- 10295 2017-07-31 SLED WITH VEHICLE BODY
- 10296 2017-08-01 SLED WITH VEHICLE BODY
- 10297 2017-08-02 SLED WITH VEHICLE BODY
- 10298 2017-08-02 SLED WITH VEHICLE BODY
- 10299 2017-08-03 SLED WITH VEHICLE BODY
