# Full-Scale Schema Audit 2011+

## Conclusion
- in_scope_tests: 3891
- out_of_scope_tests: 0
- missing_test_date: 0
- date_parse_failed: 0
- semantic_hard_failures: 0
- schema_contract_hard_failures: 0
- endpoint_matrix_hard_failures: 0
- source_payload_immutability: pass
- prohibited_payload_index_check: pass

## Canonical Duplicate Groups

| table | group_count | row_count |
|---|---:|---:|
| barriers | 0 | 0 |
| instrumentation_channels | 0 | 0 |
| media_assets | 0 | 0 |
| occupants | 0 | 0 |
| restraints | 0 | 0 |
| test_participants | 0 | 0 |
| vehicles | 0 | 0 |

## Endpoint Payload Observation Coverage

| endpoint | source_payloads | observations |
|---|---:|---:|
| barrier_info | 3891 | 3891 |
| instrumentation_info | 25524 | 25524 |
| intrusion_info | 4048 | 4048 |
| metadata_export | 3891 | 3891 |
| multimedia_files | 3891 | 3891 |
| occupant_info | 3891 | 3891 |
| restraint_info | 5618 | 5618 |
| test_detail | 3891 | 3891 |
| test_summary | 3891 | 3891 |
| vehicle_documents | 3891 | 3891 |
| vehicle_info | 3891 | 3891 |

## Source Conflict Summary
- total_conflicts: 9447
- P0/P1/P2/P3: 0/0/0/9447
- by_class: {'benign_alias_difference': 3412, 'numeric_rounding_difference': 6035}

## Manual Domain Review Backlog
- unmapped_fields: 465
- P0/P1 schema recommendations: 0/0
- P2/P3 schema recommendations: 117/19

## Data Package Invariant
- candidate_assets: 19217
- classified_data_package_assets: 19222
- candidate_unclassified_count: 0
- status: pass
