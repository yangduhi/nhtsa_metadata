# Endpoint Entity Matrix v1.5

## Summary
- endpoint_rows: 21
- status_counts: {'documented_exception': 10, 'pass': 11}
- Source of detail: `data/schema/endpoint_entity_matrix_v1_5.csv`.

## Matrix
| endpoint_name | collection_decision | payload_count | observation_count | mapped_entity_types | field_catalog_rows | relationship_count | contract_status | exception_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| test_results | required_discovery_not_persisted | 0 | 0 | discovery_manifest_candidate | 0 | 0 | documented_exception | required_discovery_not_persisted |
| search | required_discovery_not_persisted | 0 | 0 | discovery_manifest_candidate | 0 | 0 | documented_exception | required_discovery_not_persisted |
| search_vehicle | optional_discovery_not_collected | 0 | 0 | discovery_manifest_candidate | 0 | 0 | documented_exception | optional_discovery_not_collected |
| search_barrier | optional_discovery_not_collected | 0 | 0 | discovery_manifest_candidate | 0 | 0 | documented_exception | optional_discovery_not_collected |
| vehicle_models | optional_discovery_not_collected | 0 | 0 | reference_dictionary | 0 | 0 | documented_exception | optional_discovery_not_collected |
| occupant_types | optional_discovery_not_collected | 0 | 0 | reference_dictionary | 0 | 0 | documented_exception | optional_discovery_not_collected |
| test_summary | required_collected | 3891 | 3891 | manifest_tests\|test_identities | 25 | 0 | pass |  |
| metadata_export | required_collected | 3891 | 3891 | manifest_tests\|vehicles\|test_participants\|barriers\|occupants\|restraints\|instrumentation_channels\|injury_metrics\|deformation_measurements\|media_assets | 236 | 858079 | pass |  |
| test_detail | optional_core_collected | 3891 | 3891 | native_test_detail | 29 | 0 | pass |  |
| vehicle_info | required_collected | 3891 | 3891 | vehicles\|test_participants | 25 | 9386 | pass |  |
| vehicle_detail | optional_detail_not_collected | 0 | 0 | native_vehicle_detail | 0 | 0 | documented_exception | optional_detail_not_collected |
| barrier_info | required_collected | 3891 | 3891 | barriers\|test_participants | 19 | 3254 | pass |  |
| occupant_info | required_collected | 3891 | 3891 | occupants | 26 | 5618 | pass |  |
| occupant_info_by_vehicle | superseded_by_test_level_occupant_info | 0 | 0 | occupants | 0 | 0 | documented_exception | superseded_by_test_level_occupant_info |
| occupant_detail | optional_detail_not_collected | 0 | 0 | native_occupant_detail | 0 | 0 | documented_exception | optional_detail_not_collected |
| restraint_info | required_collected | 5618 | 5618 | restraints | 16 | 12526 | pass |  |
| intrusion_info | required_collected | 4048 | 4048 | intrusion_measurements | 24 | 0 | pass |  |
| instrumentation_info | required_collected | 25524 | 25524 | instrumentation_channels | 24 | 470435 | pass |  |
| instrumentation_detail | deferred_optional_not_collected | 0 | 0 | instrumentation_channel_details | 0 | 0 | documented_exception | deferred_optional_not_collected |
| multimedia_files | required_collected | 3891 | 3891 | native_multimedia_listing | 29 | 0 | pass |  |
| vehicle_documents | required_collected | 3891 | 3891 | media_assets | 15 | 19217 | pass |  |
