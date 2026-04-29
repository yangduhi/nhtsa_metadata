# DB Schema

Phase 2 implements the initial SQLAlchemy/Alembic schema.

## Raw / Provenance

- `collection_runs`
- `collection_run_items`
- `source_endpoints`
- `source_payloads`
- `source_payload_observations`
- `source_payload_sections`
- `source_field_catalog`
- `source_conflicts`
- `canonical_row_sources`

`source_payloads` is immutable by `(endpoint_name, canonical_url_hash, payload_hash)`.
`source_payload_observations` records each fetch observation.
`canonical_row_sources` is idempotent by `(table_name, row_id, source_payload_id,
source_row_path, source_row_hash)` so repeated observations can attach to one canonical row.

## Canonical

- `tests`
- `test_participants`
- `vehicles`
- `barriers`
- `occupants`
- `restraints`
- `instrumentation_channels`
- `instrumentation_channel_details`
- `injury_metrics`
- `deformation_measurements`
- `intrusion_measurements`
- `media_assets`
- `code_values`

Canonical domain tables include lineage columns where rows are derived from raw source payloads:
`source_payload_id`, `source_endpoint_name`, `source_section_name`, `source_row_path`,
`source_row_hash`, `raw_row_json`, and `extra_json`.

`restraints` uses semantic identity columns `semantic_key` and `semantic_hash`.
The unique canonical identity is `(test_id, semantic_hash)`; duplicate source observations
attach through `canonical_row_sources` instead of creating additional restraint rows.

`media_assets` stores `asset_kind` and optional `asset_subtype`. Data-package candidates such
as UDS, EV, ABF, ISO, TDMS, and ZIP are represented with `asset_kind = data_package` and the
specific subtype in `asset_subtype`.

## Read Model

- `test_filter_summary`
- `test_classification`
- `test_facets`
- `asset_summary`
- `field_coverage_snapshots`

Read models are rebuildable derivatives, not source of truth.
`test_classification` stores derived crash-test family fields such as impact direction,
counterparty kind, and classification status.

## Migration

The initial Alembic revision is `0001_initial_schema`.
