# 2026-05-03 | Stage K | PASS WITH CONFIG CAVEAT | Load Cell Barrier Classification v2.2.0

## Scope

- Config: `docs/nhtsa_barrier_load_cell_classification_config_v2.2.0.json`
- DB: `data/full_2011plus_metadata_only_refresh_2026-05-03.sqlite`
- Live API: not used
- Target universe: barrier-side load-cell attachment families from v2.2.0:
  - `LOAD CELL A1` ... `LOAD CELL D9`
  - `LOAD CELL ROW n COLUMN m`
  - `LOAD CELL POLE n`
  - legacy `POLE` with `INSCOM` carrying `LOAD CELL n`

## Result

v2.2.0 closes the barrier load-cell classification universe when applying the rule intent plus a small barrier-shape alias layer.

| Application mode | Candidate tests | Classified | Unclassified | Interpretation |
|---|---:|---:|---:|---|
| Strict JSON exact `barrier_shape_allowed` match | 1,137 | 1,127 | 10 | Machine-exact config leaves DB shape-alias gaps |
| v2.2.0 intent with barrier-shape aliases | 1,137 | 1,137 | 0 | Matches config expected coverage |

The v2.2.0 expected coverage section is correct only if the classifier normalizes or aliases several DB `barriers.shape` values before applying `barrier_shape_allowed`.

## Alias Cases Required

| Test count | Raw `barriers.shape` | Assigned rule | Reason |
|---:|---|---|---|
| 7 | `8 X 16 LOAD CELL BARRIER` | `advanced_11x16_128_active` | Attachment occupancy is 128 force channels, active rows 4-11, cols 1-16 |
| 1 | `OTHER` | `extended_height_10x16_160` | Test title says high-resolution load cell barrier; attachment occupancy is 160 force channels, rows 2-11, cols 1-16 |
| 2 | `FLAT BARRIER` | `legacy_4x9_us_ncap` | Legacy `LOAD CELL A-D` / cols 1-9 pattern, 36 channels |

Raw-shape alias test numbers:

- `8 X 16 LOAD CELL BARRIER`: `8066`, `8071`, `8077`, `8091`, `8100`, `8151`, `8155`
- `OTHER`: `8603`
- `FLAT BARRIER`: `9662`, `9989`

## v2.2.0 Classification Summary

Alias-assisted rule application:

| Classification id | Tests | Channels | Force channels | Moment channels | Status |
|---|---:|---:|---:|---:|---|
| `legacy_4x9_us_ncap` | 112 | 4,032 | 4,032 | 0 | covered |
| `high_res_8x16_128` | 2 | 768 | 256 | 512 | covered_with_geometry_caveat |
| `partial_8x16_127_missing_one_force_channel` | 8 | 1,016 | 1,016 | 0 | covered_with_mask |
| `extended_height_10x16_160` | 48 | 13,184 | 7,680 | 5,504 | covered |
| `advanced_11x16_128_active` | 96 | 22,784 | 12,288 | 10,496 | covered_with_active_cell_mask |
| `advanced_11x16_176_full` | 283 | 136,400 | 49,808 | 86,592 | covered |
| `side_pole_load_cell_8` | 588 | 4,701 | 4,701 | 0 | covered_with_mask |
| Total | 1,137 | 182,885 | 79,781 | 103,104 | covered |

## Mask Findings

Partial 8x16 wall:

- `7201`, `7203`, `7339`, `7347`, `7350`, `7358`, `7362`, `7370`
- missing expected force cell: `(row=2, col=16)`
- assigned rule: `partial_8x16_127_missing_one_force_channel`

Pole barrier mask cases:

- `11656`: 6 force channels; missing pole indices `7`, `8`
- `14604`: 6 force channels; missing pole indices `1`, `2`
- `14617`: 9 force channels; duplicate pole index `8`

## Config Caveat

The current JSON is semantically sufficient but not fully machine-executable as strict exact-match rules. To make strict implementation reproduce `expected_current_db_coverage_after_rules`, add an explicit `barrier_shape_aliases` or `shape_normalization_policy`, for example:

```json
{
  "barrier_shape_aliases": {
    "LOAD_CELL_BARRIER": [
      "LOAD CELL BARRIER",
      "8 X 16 LOAD CELL BARRIER",
      "8 X 16 + 6 LOAD CELL BARRIER",
      "FLAT BARRIER"
    ],
    "POLE": ["POLE"],
    "LOAD_CELL_BARRIER_BY_TITLE_AND_OCCUPANCY_REVIEW": ["OTHER"]
  }
}
```

For `OTHER`, keep the alias conditional: require `LOAD CELL BARRIER` evidence in title/commentary plus a valid row/column occupancy match. Do not globally alias all `OTHER` barriers.

## Verification

Executed locally with `.venv` and SQLite only:

- loaded `docs/nhtsa_barrier_load_cell_classification_config_v2.2.0.json`
- scanned `instrumentation_channels` where `sensor_type = 'LOAD CELL'`
- joined `barriers.shape` by `test_no`
- parsed attachment patterns from v2.2.0
- separated strict exact-shape application from alias-assisted application
- compared actual coverage with `expected_current_db_coverage_after_rules`
