# 2026-05-02 | Classifier v1.4 Failure Package | RECORDED | Full-Scale Code Values Rebuild 2011+

## Conclusion
- code_sets: 17
- inserted: 757
- high_risk_blocked_values: 0

## Code Set Distribution

| code_set | values | observed_count | observed_test_count | source_endpoint |
|---|---:|---:|---:|---|
| sensor_type | 28 | 470435 | 15881 | instrumentation_info |
| sensor_attachment | 559 | 470435 | 153243 | instrumentation_info |
| sensor_axis | 30 | 470435 | 22056 | instrumentation_info |
| data_measurement_unit | 28 | 470435 | 19016 | instrumentation_info |
| data_status | 8 | 470389 | 7975 | instrumentation_info |
| channel_status | 4 | 470042 | 6178 | instrumentation_info |
| occupant_location | 6 | 5875 | 5872 | occupant_info |
| occupant_type | 19 | 5875 | 4585 | occupant_info |
| restraint_type | 25 | 12492 | 8360 | restraint_info |
| restraint_deployment | 5 | 12468 | 5493 | restraint_info |
| barrier_rigidity | 2 | 1409 | 1409 | barrier_info |
| barrier_shape | 10 | 1409 | 1409 | barrier_info |
| asset_kind | 5 | 289821 | 13718 | media_assets |
| asset_subtype | 8 | 289821 | 25560 | media_assets |
| test_configuration_key | 15 | 3815 | 3815 | test_summary |
| classification_status | 2 | 3891 | 3891 | test_classification |
| participant_kind | 3 | 6320 | 6161 | test_participants |

## Excluded Policy
- File internals, identifiers, and numeric measurements remain excluded from code value promotion.
- The code_values table is a rebuildable derived registry, not source of truth.
