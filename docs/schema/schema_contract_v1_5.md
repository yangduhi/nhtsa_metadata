# Schema Contract v1.5

## Purpose
Schema contract v1.5 freezes the metadata-only schema surface for the 2011+ NHTSA crash test corpus independently of classifier acceptance. It describes source payloads, endpoints, fields, code values, native entities, relationships, and provenance without changing classifier rules.

## Source Baseline
- source_system: `nhtsa_crash`
- source_db: `D:\vscode\nhtsa_metadata_stage_d\data\full_2011plus_metadata_only_stage_d_2026-04-30.sqlite`
- source_db_size_bytes: 2641743872
- manifest: `D:\vscode\nhtsa_metadata_stage_d\data\full_2011plus_authoritative_manifest.csv`
- manifest_sha256: `b4a1262938d33793bff0d4aca78222e4bab51c7253d4084fbb80597096abe6be`
- manifest_rows: 3891
- source_payloads: 66318
- payload_observations: 66318
- code_values: 757

## Identity Rule
The canonical test identity is not a single naked number. The contract identity is `canonical_test_uid = source_system + ':' + native_test_id`, for example `nhtsa_crash:10001`.

## Classification Boundary
Classification labels are derived semantic outputs and must not be stored directly on `manifest_tests`. Derived classification results must be explainable through `classification_evidence`, linked to a source payload, endpoint, field path, or explicit documented exception. This contract defines the evidence surface only; it does not change classifier logic.

## Conceptual Tables
| conceptual_table | role | current_mapping |
| --- | --- | --- |
| source_systems | Registers external source authorities. | new v1.5 contract table |
| source_endpoints | Defines endpoint names, paths, collection groups, and policy flags. | existing DB table plus code endpoint definitions |
| endpoint_requests | Records request-level provenance before payload persistence. | new v1.5 contract table; current payload rows carry request_url |
| source_payloads | Stores immutable raw source payload JSON. | existing DB table |
| manifest_tests | Stores 2011+ in-scope manifest rows without derived classification labels. | new v1.5 contract table; current DB table is tests plus manifest CSV |
| test_identities | Maps source native IDs to canonical_test_uid. | new v1.5 contract table; canonical_test_uid is derived |
| payload_observations | Records fetch observation metadata for persisted payloads. | current DB table source_payload_observations |
| entity_instances | Represents native source entities without forcing a vehicle-centric model. | new v1.5 contract table; current canonical tables remain native |
| field_catalog | Describes observed JSON paths and contract treatment. | new v1.5 contract table; current DB table source_field_catalog |
| field_occurrences | Links field catalog entries to payload-level observations. | new v1.5 contract table |
| code_sets | Defines approved rebuildable code dictionaries. | new v1.5 contract table |
| code_values | Stores rebuildable code values. | existing DB table |
| relationship_edges | Describes entity and provenance relationships. | new v1.5 contract table |
| semantic_concepts | Defines derived semantic concepts independent of raw source payloads. | new v1.5 contract table |
| classification_rules | Registers rule metadata without changing rule logic. | new v1.5 contract table |
| classification_evidence | Links derived classification labels to source evidence. | new v1.5 contract table |
| schema_versions | Records contract version metadata. | new v1.5 contract table |
| audit_results | Records audit results and documented exceptions. | new v1.5 contract table |

## Audit Summary
| audit_id | status | hard_failures | documented_exceptions |
| --- | --- | --- | --- |
| audit_1_source_baseline_verification | pass | 0 | 0 |
| audit_2_endpoint_to_entity_coverage | pass | 0 | 10 |
| audit_3_observed_json_path_coverage | pass | 0 | 420 |
| audit_4_code_linkage | documented_exception | 0 | 25 |
| audit_5_orphan_entity | pass | 0 | 0 |
| audit_6_provenance_completeness | pass | 0 | 0 |
| audit_7_migration_sanity | pass | 0 | 0 |

## Acceptance Rule
`ACCEPTED` is allowed only when source baseline verification passes, endpoint hard failures are zero, manifest row mismatch is zero, no large DB artifact is staged, migration/test evidence is recorded, and unknown/code/orphan/provenance exceptions are all documented.
