# Schema

## Scope

The schema is for a 2011+ NHTSA crash test metadata-only catalog. Canonical and
read-model rows are limited to records with parseable `test_date >= 2011-01-01`.

The authoritative detailed schema contract remains:

- `docs/db_schema.md`
- `docs/db_schema_contract.md`

This document is the handoff summary.

## Layers

| Layer | Examples | Rule |
|---|---|---|
| Raw/provenance | `source_payloads`, `source_payload_sections`, `canonical_row_sources` | source of truth; preserved and immutable |
| Canonical | `tests`, `vehicles`, `barriers`, `instrumentation_channels`, `media_assets` | rebuildable normalized domain rows |
| Read model | `test_filter_summary`, `test_classification`, `test_facets`, `asset_summary` | rebuildable filtering/audit projections |
| Governance | `discovery_runs`, `discovery_manifest_rows`, `discovery_authority_decisions` | records why a test entered the corpus |

## Final Output DB Baseline

| Table | Rows |
|---|---:|
| `tests` | 3,900 |
| `vehicles` | 4,705 |
| `source_payloads` | 66,477 |
| `source_payload_observations` | 66,477 |
| `source_payload_sections` | 101,577 |
| `media_assets` | 290,845 |
| `instrumentation_channels` | 471,566 |
| `canonical_row_sources` | 1,382,222 |
| `test_classification` | 3,900 |
| `test_filter_summary` | 3,900 |
| `barrier_load_cell_classification` | 1,137 |
| `barrier_load_cell_channel_map` | 0 |

## Vehicle Filter Fields

Promoted vehicle fields:

- `body_type`
- `curb_weight_raw` / `curb_weight`
- `vehicle_length_raw` / `vehicle_length`
- `vehicle_width_raw` / `vehicle_width`
- `wheelbase_raw` / `wheelbase`
- `vax_crush_distance_raw` / `vax_crush_distance`

The promotion logic is isolated in
`src/nhtsa_metadata/services/vehicle_filter_fields.py`.

## Classification and Disposition

Project completion is based on `accounted_for_count`, not all-row canonical
classification.

Final tracked acceptance metrics:

- `total_count = 3900`
- `canonical_label_classified_count = 3881`
- `adjudicated_noncanonical_count = 19`
- `unadjudicated_count = 0`
- `known_false_positive_count = 0`
- `accounted_for_count = 3900`

The 19 noncanonical rows remain final dispositions and are not forced into
canonical labels.
