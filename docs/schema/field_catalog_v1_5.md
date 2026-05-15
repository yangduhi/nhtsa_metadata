# Field Catalog v1.5

## Summary
- field_catalog_rows: 468
- code_linked_rows: 25
- contract_status_counts: {'documented_exception': 420, 'mapped': 23, 'code_linked': 25}
- Source of detail: `data/schema/field_catalog_v1_5.csv`.

## Field Coverage By Endpoint
| endpoint_name | field_rows |
| --- | --- |
| metadata_export | 236 |
| multimedia_files | 29 |
| test_detail | 29 |
| occupant_info | 26 |
| test_summary | 25 |
| vehicle_info | 25 |
| instrumentation_info | 24 |
| intrusion_info | 24 |
| barrier_info | 19 |
| restraint_info | 16 |
| vehicle_documents | 15 |

## Required Columns
`source_system`, `endpoint_name`, `entity_type`, `raw_field_name`, `normalized_field_name`, `json_path`, `observed_data_type`, `contract_data_type`, `unit`, `range_min`, `range_max`, `max_length`, `nullable_observed`, `nullable_contract`, `is_code`, `code_set_name`, `code_set_source`, `first_seen_payload_id`, `last_seen_payload_id`, `occurrence_count`, `example_values`, `contract_status`, and `exception_reason` are present in the CSV artifact.
