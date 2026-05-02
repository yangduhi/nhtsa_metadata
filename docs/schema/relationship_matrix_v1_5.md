# Relationship Matrix v1.5

## Summary
- relationship_rows: 26
- Native component, biomechanics, CADB, and vehicle crash data entities are preserved and linked through relationship edges rather than forced into one vehicle-centric model.
- Source of detail: `data/schema/relationship_matrix_v1_5.csv`.

## Relationships
| relationship_name | from_entity_type | from_key | to_entity_type | to_key | cardinality | source_endpoint_name | contract_status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| source_system_has_endpoint | source_systems | source_system | source_endpoints | endpoint_name | 1:N |  | pass |
| endpoint_has_request | source_endpoints | endpoint_name | endpoint_requests | endpoint_name | 1:N |  | pass |
| request_persists_payload | endpoint_requests | request_url_hash | source_payloads | payload_hash | 1:1 |  | pass |
| payload_has_observation | source_payloads | id | payload_observations | source_payload_id | 1:N |  | pass |
| manifest_has_identity | manifest_tests | canonical_test_uid | test_identities | canonical_test_uid | 1:N | test_summary | pass |
| payload_links_manifest_test | source_payloads | source_system:native_test_id | manifest_tests | canonical_test_uid | N:1 |  | pass |
| field_catalog_links_code_set | field_catalog | code_set_name | code_sets | code_set_name | N:1 |  | pass |
| code_set_has_values | code_sets | code_set_name | code_values | code_set | 1:N |  | pass |
| semantic_concept_has_rules | semantic_concepts | id | classification_rules | semantic_concept_id | 1:N |  | pass |
| classification_has_evidence | classification_rules | rule_id | classification_evidence | classification_rule_id | 1:N |  | pass |
| classification_evidence_links_payload | classification_evidence | source_payload_id | source_payloads | id | N:1 |  | pass |
| classification_evidence_links_field | classification_evidence | field_catalog_id | field_catalog | id | N:1 |  | pass |
| test_has_vehicle | manifest_tests | canonical_test_uid | vehicles | test_id | 1:N | vehicle_info | pass |
| test_has_barrier | manifest_tests | canonical_test_uid | barriers | test_id | 1:N | barrier_info | pass |
| test_has_participant | manifest_tests | canonical_test_uid | test_participants | test_id | 1:N | vehicle_info | pass |
| test_has_occupant | manifest_tests | canonical_test_uid | occupants | test_id | 1:N | occupant_info | pass |
| vehicle_has_occupant | vehicles | id | occupants | vehicle_id | 1:N | occupant_info | pass |
| test_has_restraint | manifest_tests | canonical_test_uid | restraints | test_id | 1:N | restraint_info | pass |
| occupant_has_restraint | occupants | id | restraints | occupant_id | 1:N | restraint_info | pass |
| test_has_instrumentation_channel | manifest_tests | canonical_test_uid | instrumentation_channels | test_id | 1:N | instrumentation_info | pass |
| test_has_injury_metric | manifest_tests | canonical_test_uid | injury_metrics | test_id | 1:N | metadata_export | pass |
| occupant_has_injury_metric | occupants | id | injury_metrics | occupant_id | 1:N | metadata_export | pass |
| test_has_deformation_measurement | manifest_tests | canonical_test_uid | deformation_measurements | test_id | 1:N | metadata_export | pass |
| vehicle_has_deformation_measurement | vehicles | id | deformation_measurements | vehicle_id | 1:N | metadata_export | pass |
| test_has_media_asset | manifest_tests | canonical_test_uid | media_assets | test_id | 1:N | vehicle_documents | pass |
| payload_has_canonical_row_source | source_payloads | id | entity_instances | source_payload_id | 1:N |  | pass |
