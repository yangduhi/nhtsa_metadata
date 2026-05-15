# Stage L Barrier Load-Cell DB Integration Result

## Scope

- Config: `docs/nhtsa_barrier_load_cell_classification_config_v2.2.2.json`
- DB validation source: `data/full_2011plus_metadata_only_refresh_2026-05-03.sqlite`
- Live NHTSA API calls: not used
- Production/raw payload rewrite: not performed

This stage integrates the v2.2.2 barrier load-cell classification system into
the metadata DB schema as a rebuildable derived read-model/evidence surface.

## Schema Changes

Added:

- `barrier_load_cell_classification`
- `barrier_load_cell_channel_map`

Updated:

- `test_filter_summary`

The classification table stores one selected v2.2.2 load-cell family assignment
per test/config/classification id. It preserves raw barrier shape,
shape-normalized key, alias rule, conditional-alias evidence, channel counts,
force/moment counts, occupancy map, duplicate/missing-channel masks, and rule
evidence.

The channel map stores the per-channel evidence surface: source channel id,
curve number, raw attachment/commentary, parsed wall row/column or pole index,
quantity type, raw/canonical axis, unit, generated LOMA-style name where a wall
cell exists, and mask flags.

`test_filter_summary` now carries:

- `load_cell_barrier_classification_ids_json`
- `load_cell_barrier_families_json`
- `load_cell_barrier_config_version`
- `load_cell_barrier_channel_count`
- `load_cell_barrier_force_channel_count`
- `load_cell_barrier_moment_channel_count`

`has_load_cell_barrier` is driven by classifier output when available and falls
back to the previous barrier shape/commentary detector for DBs without
classification rows.

## Classification Rules Reflected

The DB read model supports these v2.2.2 classification ids:

| Classification id | Family | Status |
|---|---|---|
| `legacy_4x9_us_ncap` | `frontal_or_flat_load_cell_wall` | `covered` |
| `high_res_8x16_128` | `frontal_or_flat_load_cell_wall` | `covered_with_geometry_caveat` |
| `partial_8x16_127_missing_one_force_channel` | `frontal_or_flat_load_cell_wall` | `covered_with_mask` |
| `extended_height_10x16_160` | `frontal_or_flat_load_cell_wall` | `covered` |
| `advanced_11x16_128_active` | `frontal_or_flat_load_cell_wall` | `covered_with_active_cell_mask` |
| `advanced_11x16_176_full` | `frontal_or_flat_load_cell_wall` | `covered` |
| `side_pole_load_cell_8` | `side_pole_load_cell_barrier` | `covered_with_mask` |

## Source Payload Use

The implementation uses existing preserved source metadata only:

- `barriers.shape`
- raw `barrierShape` / `BARSHPD`
- raw `barrierCommentary` / `BARCOM`
- `instrumentation_channels.sensor_type`
- `instrumentation_channels.sensor_attachment`
- `instrumentation_channels.sensor_axis`
- `instrumentation_channels.unit_raw`
- raw `SENTYPD`, `SENATTD`, `AXISD`, `YTYPE`, `YUNITSD`, `INSCOM`

`barrierShape = "LOAD CELL BARRIER"` and
`barrierCommentary = "ADVANCED RESEARCH LOAD CELL BARRIER"` are preserved in
the evidence path. Conditional `OTHER` aliasing remains restricted to a reviewed
load-cell barrier evidence path plus the 160-force 10x16 occupancy signature.

## Full DB Read-Only Validation

The full DB was opened read-only with SQLite immutable mode. No DB writes were
performed.

| Classification id | Tests | Channels | Force channels | Moment channels |
|---|---:|---:|---:|---:|
| `legacy_4x9_us_ncap` | 112 | 4,032 | 4,032 | 0 |
| `high_res_8x16_128` | 2 | 768 | 256 | 512 |
| `partial_8x16_127_missing_one_force_channel` | 8 | 1,016 | 1,016 | 0 |
| `extended_height_10x16_160` | 48 | 13,184 | 7,680 | 5,504 |
| `advanced_11x16_128_active` | 96 | 22,784 | 12,288 | 10,496 |
| `advanced_11x16_176_full` | 283 | 136,400 | 49,808 | 86,592 |
| `side_pole_load_cell_8` | 588 | 4,701 | 4,701 | 0 |
| Total | 1,137 | 182,885 | 79,781 | 103,104 |

This matches
`expected_current_db_coverage_after_rules.classification_summary_alias_assisted`
in v2.2.2.

## Notable Implementation Detail

Some DB channels identify quantity through unit fields only:

- `YTYPE = null`, `YUNITSD = "NEWTONS"`
- `YTYPE = null`, `YUNITSD = "NEWTON-METERS"`

The classifier treats these as force and moment respectively. This is required
for the v2.2.2 read-only full DB validation to reach 1,137/1,137 coverage.

## Validation Commands

- `pytest tests\test_barrier_load_cell_classifier.py tests\test_db_migrations.py tests\test_db_models.py -q`
- `ruff check src tests`
- `mypy src\nhtsa_metadata`
- read-only SQLite full DB classification scan against
  `data/full_2011plus_metadata_only_refresh_2026-05-03.sqlite`

## Result

Stage L is implementation-complete for DB reflection of the v2.2.2 load-cell
barrier classification system.

The implementation does not parse waveform data and does not validate physical
load-cell geometry from PDFs. It is metadata-level classification and evidence
lineage only.
