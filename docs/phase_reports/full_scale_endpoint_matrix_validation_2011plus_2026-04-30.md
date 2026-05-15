# Endpoint Matrix Contract 2011+

## Result
- result: pass
- hard failures: 0
- warnings: 0

## Manifest Gate
- row_count: 3891
- date_range: ['2011-01-03', '2025-09-25']
- duplicate_test_no: 0
- missing_or_parse_failed_date: 0
- pre_2011_rows: 0
- scope_status_values: ['in_scope']
- anchors: {7201: True, 10001: True, 10003: True}
- year_distribution: {2011: 345, 2012: 434, 2013: 470, 2014: 360, 2015: 249, 2016: 412, 2017: 321, 2018: 205, 2019: 185, 2020: 226, 2021: 170, 2022: 118, 2023: 164, 2024: 156, 2025: 76}
- test_type_distribution: {'CALIBRATION TEST': 9, 'EXPERIMENTAL NEW CAR ASSESSMENT TEST': 330, 'FMVSS 208 OCCUPANT CRASH PROTECTION': 336, 'FMVSS 213 CHILD RESTRAINT SYSTEMS': 266, 'FMVSS 214 SIDE IMPACT PROTECTION': 18, 'FMVSS 226 EJECTION MITIGATION': 76, 'FMVSS 301 FUEL SYSTEM INTEGRITY': 19, 'FMVSS COMPLIANCE TEST - UNSPECIFIED': 7, 'MODIFIED VEHICLE TEST': 25, 'NEW CAR ASSESSMENT TEST': 1064, 'OCCUPANT PERFORMANCE TEST': 181, 'OPTIONAL NEW CAR ASSESSMENT TEST': 348, 'OTHER': 91, 'OUT OF POSITION (TWG) SIDE AIRBAG DEPLOYMENT TESTS': 71, 'RESEARCH': 81, 'RESEARCH SAFETY VEHICLE TEST': 128, 'RMDB INTO FRONT 15 DEGREE STATIONARY VEHICLE, OVERLAP=35 PERCENT': 145, 'RMDB INTO FRONT 7 DEGREE STATIONARY VEHICLE, OVERLAP=20 PERCENT': 18, 'TEST PROCEDURE DEVELOPMENT': 55, 'UNKNOWN': 605, 'VALIDATION NEW CAR ASSESSMENT TEST': 8, 'VEHICLE OPERATIONAL SAFETY-CRITICAL SCENARIOS': 1, 'Validation New Car Assessment Test': 9}
- test_configuration_distribution: {'FORWARD COLLISION WARNING PERFORMANCE TEST': 45, 'IMPACTOR INTO IMPACTOR': 6, 'IMPACTOR INTO VEHICLE': 811, 'LANE DEPARTURE WARNING PERFORMANCE TEST': 31, 'LOW RISK DEPLOYMENT': 261, 'OTHER': 21, 'PEDESTRIAN': 195, 'ROLLOVER': 130, 'SLED WITH VEHICLE BODY': 156, 'SLED WITHOUT VEHICLE BODY': 565, 'STATIC AIR BAG TEST SIDE': 235, 'TRAFFIC JAM ASSIST': 1, 'UNKNOWN': 76, 'VEHICLE INTO BARRIER': 730, 'VEHICLE INTO POLE': 616, 'VEHICLE INTO VEHICLE': 12}
- classification_distribution: {'airbag_static_or_low_risk': 496, 'frontal_barrier': 730, 'non_crash_adas': 77, 'pole': 616, 'rollover': 130, 'side_impactor': 811, 'sled': 721, 'unknown_or_other': 298, 'vehicle_to_vehicle': 12}

## Endpoints
- vehicle-database-test-results -> `test_results` decision=required payloads=0 code=True db=False
- vehicle-database-test-results/by-search -> `search` decision=required payloads=0 code=True db=False
- test_summary / test-no/{testNo} -> `test_summary` decision=required payloads=3891 code=True db=False
- test_detail / get-test-detail/{testNo} -> `test_detail` decision=optional_core payloads=3891 code=True db=False
- metadata_export / metadata/{testNo} -> `metadata_export` decision=required payloads=3891 code=True db=False
- vehicle_info -> `vehicle_info` decision=required payloads=3891 code=True db=False
- vehicle_detail_info -> `vehicle_detail` decision=optional_detail payloads=0 code=True db=False
- barrier_info -> `barrier_info` decision=required payloads=3891 code=True db=False
- occupant_info -> `occupant_info` decision=required payloads=3891 code=True db=False
- occupant_detail_information -> `occupant_detail` decision=optional_detail payloads=0 code=True db=False
- restraint_info -> `restraint_info` decision=required payloads=5618 code=True db=False
- intrusion_info -> `intrusion_info` decision=required payloads=4048 code=True db=False
- instrumentation_info -> `instrumentation_info` decision=required payloads=25524 code=True db=False
- instrumentation_detail_info -> `instrumentation_detail` decision=deferred_optional payloads=0 code=True db=False
- multimedia_files -> `multimedia_files` decision=required payloads=3891 code=True db=False
- vehicle_documents -> `vehicle_documents` decision=required payloads=3891 code=True db=False

## Instrumentation Detail Decision
- decision: deferred_optional
- reason: per-curve detail collection can multiply request volume by instrumentation_channels; v1.1 preserves schema support but does not require it for metadata-only full-scale collection

## Hard Failures
- none

## Warnings
- none
