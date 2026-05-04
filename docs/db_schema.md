# DB Schema

Schema v1.0 defines a 2011+ NHTSA crash test metadata-only database.

Canonical/read-model rows are limited to tests with `test_date >= 2011-01-01`. `test_no` and `modelYear` are not scope criteria.

## Layer Policy

- Raw/provenance tables are the durable source of truth.
- Canonical tables are normalized, rebuildable domain entities.
- Read-model tables are rebuildable derivatives for filtering, API responses, and audit summaries.
- Files, media payloads, waveform data, and package internals are not downloaded or parsed.

## Raw / Provenance Tables

| Table | Source of truth | Normalized meaning | Key / lineage / rebuild policy |
|---|---|---|---|
| `collection_runs` | yes | One collect/rebuild/backfill operation. | `run_uuid` unique; records source, mode, status, options, and errors. |
| `collection_run_items` | yes | Per-test/per-endpoint run item. | FK to `collection_runs`; `status` includes succeeded/skipped/failure states. |
| `source_endpoints` | yes | Endpoint registry and parser contract. | `name` unique; stores path template, group, pagination, allow-empty policy. |
| `source_payloads` | yes | Immutable raw payload store. | Unique `(endpoint_name, canonical_url_hash, payload_hash)`; stores payload JSON and request metadata. |
| `source_payload_observations` | yes | Repeated fetch observations of immutable payloads. | FK to `source_payloads` and collection run/item. |
| `source_payload_sections` | yes | Parsed payload section inventory. | Unique `(source_payload_id, section_name, json_path)`. |
| `source_field_catalog` | yes | Wildcard-normalized field coverage catalog. | Unique `(endpoint_name, section_name, field_path, observed_type)`. |
| `source_conflicts` | yes | Provenance conflict registry. | Keeps conflict type, source payload pair, field path, and status. |
| `canonical_row_sources` | yes | Link from canonical/read-model rows to raw rows. | Unique `(table_name, row_id, source_payload_id, source_row_path, source_row_hash)`. |
| `discovery_runs` | governance | One manifest discovery/validation/merge operation. | Stores authority, command, manifest hash, date range, row counts, and gates. |
| `discovery_manifest_rows` | governance | Per-test manifest authority row. | Unique `(discovery_run_id, test_no)` and `(discovery_run_id, row_hash)`; stores live/reference presence and authority status. |
| `discovery_authority_decisions` | governance | Documented selection of discovery authority. | Stores selected authority, counts, decision status, and reason. |

Discovery tables are an operational/provenance layer. They explain why a `test_no`
is in the full-scale input manifest; they do not make the reference DB a canonical
source of truth.

## Canonical Tables

| Table | Source of truth | Normalized entity | Natural / semantic key | Lineage and rebuild policy |
|---|---|---|---|---|
| `tests` | derived | One in-scope crash test. | `test_no` unique; `test_date >= 2011-01-01`. | Has lineage columns and is rebuildable from summary/detail/export payloads. |
| `test_participants` | derived | Subject vehicle, impactor vehicle, or barrier participant. | `test_id`, `participant_kind`, source vehicle/barrier identity. | Preserves source row and participant classification reason. |
| `vehicles` | derived | Canonical vehicle row, including make/model/year, body type, speed, weight, length, width, wheelbase, and crush distance fields. | `test_id`, `source_vehicle_no`, `source_row_hash`. | Raw vehicle details remain in `raw_row_json`; repeated observations attach through `canonical_row_sources`. |
| `barriers` | derived | Semantic-deduped barrier. | `test_id`, `source_row_hash`; semantic audit dedupes metadata_export/detail duplicates. | Barrier empty endpoint is allowed when source returns successful empty payload. |
| `occupants` | derived | Normalized occupant slot. | `test_id`, `source_vehicle_no`, `occupant_location_raw`, `source_row_hash`. | Source observations attach through `canonical_row_sources`; read models use normalized slots. |
| `restraints` | derived | Occupant-context restraint assignment. | `test_id`, `restraint_subject_kind`, `restraint_subject_semantic_hash`, `semantic_hash`. | Must keep occupant or subject context; repeated source observations attach through `canonical_row_sources`. |
| `instrumentation_channels` | derived | Canonical channel. | Unique `(test_id, curve_no)`. | Sensor type/location/attachment/axis/unit/status are canonical columns; waveform is not parsed. |
| `instrumentation_channel_details` | derived | Optional channel detail JSON. | FK `channel_id`. | Detail JSON is rebuildable and not source of truth. |
| `barrier_load_cell_classification` | derived | Barrier-side load-cell family assignment from v2.2.3 shape-normalized metadata rules and DB read-model contract. | Unique `(test_no, config_version, classification_id)`. | Rebuildable from `barriers` plus `instrumentation_channels`; preserves raw barrier shape, normalized shape key, alias evidence, occupancy/mask summary, and force/moment counts. |
| `barrier_load_cell_channel_map` | derived | Per-channel evidence surface for the selected barrier load-cell classification. | Unique `(classification_id, instrumentation_channel_id)`. | Preserves parsed row/column or pole index, raw attachment/commentary, quantity, axis, unit, generated LOMA-style name where applicable, and mask flags. |
| `injury_metrics` | derived | Occupant injury metric. | `test_id`, optional `occupant_id`, `metric_code`. | Keeps raw and numeric parsed values. |
| `deformation_measurements` | derived | Vehicle deformation measurement. | `test_id`, optional `vehicle_id`, `measurement_code`. | Keeps raw and numeric parsed values. |
| `intrusion_measurements` | derived | Vehicle intrusion measurement. | `test_id`, optional `vehicle_id`, `measurement_code`. | Empty intrusion payload is successful source evidence; canonical rows may be zero. |
| `media_assets` | derived | URL/metadata registry item. | Unique `(test_id, asset_kind, canonical_url_hash)`. | No download; data packages store `asset_kind=data_package` and `asset_subtype`. |
| `code_values` | derived | Dictionary/domain registry. | Unique `(code_set, code_value)`. | Rebuildable from canonical/read-model tables; not source of truth. |

All canonical tables derived from source rows use lineage columns where applicable: `source_payload_id`, `source_endpoint_name`, `source_section_name`, `source_row_path`, `source_row_hash`, `raw_row_json`, and `extra_json`.

## Read Model Tables

| Table | Source of truth | Meaning | Key / rebuild policy |
|---|---|---|---|
| `test_filter_summary` | derived | One-row-per-test filter summary, including vehicle spec min/max fields, load-cell barrier flag, and v2.2.3 load-cell classification summary fields. | `test_id` and `test_no` unique; rebuildable. |
| `test_classification` | derived | Crash family / impact direction / counterparty classification. | `test_id` and `test_no` unique; unknown must be audited. |
| `test_facets` | derived | Global facet values and counts. | Unique `(facet_name, facet_value)`; absent `dummy_type` is accepted warning when no stable value is observed. |
| `asset_summary` | derived | Per-test asset kind counts. | Unique `(test_id, asset_kind)`. |
| `field_coverage_snapshots` | derived | Point-in-time field coverage/audit snapshot. | FK to run when available; JSON is generated report data. |

## v1.0 Decisions

- `occupants` = normalized occupant slots.
- `restraints` = occupant-context restraint assignments.
- `barriers` = semantic dedupe across `metadata_export` and `barrier_info`.
- `instrumentation_channels` = `test_id + curve_no` canonical channel.
- `media_assets` = URL/metadata registry only.
- `intrusion_info` = successful empty payloads are stored and do not imply collection failure.
- `data_package` = asset registry only; package contents are not parsed.
- `source_payloads` = immutable raw/provenance store.
- Read models = rebuildable derivatives.

## Index Policy

Current SQLite indexes remain conservative and are limited to identifier/FK/filter paths already declared by SQLAlchemy. `payload_json` and `raw_row_json` whole-column indexes are prohibited.

Full-scale/PostgreSQL index candidates are documented in `docs/phase_reports/schema_v1_0_index_and_read_model_plan.md` and require measured need before migration.

## Migration

The initial Alembic revision is `0001_initial_schema`. Schema v1.2 adds
`0002_discovery_provenance` for discovery authority and manifest lineage tables.
