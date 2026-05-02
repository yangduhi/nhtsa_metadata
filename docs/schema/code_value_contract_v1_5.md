# Code Value Contract v1.5

## Summary
- code_sets: 17
- code_values: 757
- Code values are rebuildable derived registries, not source of truth.
- Source of detail: `data/schema/code_sets_v1_5.csv` and `data/schema/code_values_v1_5.csv`.

## Code Sets
| code_set_name | source_endpoint_name | source_field_path | entity_type | derived_field_name | value_count | observed_count | observed_test_count | contract_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| asset_kind | media_assets | media_assets.asset_kind | media_assets | asset_kind | 5 | 289821 | 13718 | pass |
| asset_subtype | media_assets | media_assets.asset_subtype | media_assets | asset_subtype | 8 | 289821 | 25560 | pass |
| barrier_rigidity | barrier_info | $.results[*].rigidOrDeformableBarrier | barriers | rigidity | 2 | 1409 | 1409 | pass |
| barrier_shape | barrier_info | $.results[*].barrierShape | barriers | shape | 10 | 1409 | 1409 | pass |
| channel_status | instrumentation_info | $.results[*].channelStatus | instrumentation_channels | channel_status | 4 | 470042 | 6178 | pass |
| classification_status | test_classification | test_classification.classification_status | test_classification | classification_status | 2 | 3891 | 3891 | pass |
| data_measurement_unit | instrumentation_info | $.results[*].dataMeasurementUnits | instrumentation_channels | unit_raw | 28 | 470435 | 19016 | pass |
| data_status | instrumentation_info | $.results[*].dataStatus | instrumentation_channels | data_status | 8 | 470389 | 7975 | pass |
| occupant_location | occupant_info | $.results[*].occupantLocation | occupants | occupant_location_normalized | 6 | 5875 | 5872 | pass |
| occupant_type | occupant_info | $.results[*].occupantType | occupants | occupant_type | 19 | 5875 | 4585 | pass |
| participant_kind | test_participants | test_participants.participant_kind | test_participants | participant_kind | 3 | 6320 | 6161 | pass |
| restraint_deployment | restraint_info | $.results[*].inflationer/BeltPretensionerDeployment | restraints | deployment_status | 5 | 12468 | 5493 | pass |
| restraint_type | restraint_info | $.results[*].restraintType | restraints | restraint_type | 25 | 12492 | 8360 | pass |
| sensor_attachment | instrumentation_info | $.results[*].sensorAttachment | instrumentation_channels | sensor_attachment | 559 | 470435 | 153243 | pass |
| sensor_axis | instrumentation_info | $.results[*].axisDirofSensor | instrumentation_channels | sensor_axis | 30 | 470435 | 22056 | pass |
| sensor_type | instrumentation_info | $.results[*].sensorType | instrumentation_channels | sensor_type | 28 | 470435 | 15881 | pass |
| test_configuration_key | test_summary | $.results[*].testConfiguration | tests | test_configuration_key | 15 | 3815 | 3815 | pass |

## Policy
Identifiers, raw URLs, file internals, and numeric measurements are not promoted to code sets. Code-like raw fields that are not part of the 17 approved rebuildable sets remain documented exceptions in the field catalog.
