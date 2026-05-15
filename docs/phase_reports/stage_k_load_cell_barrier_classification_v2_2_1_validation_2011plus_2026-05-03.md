# 2026-05-03 | Stage K | PASS | Load Cell Barrier Classification v2.2.1 Validation

## Scope

- Config: `docs/nhtsa_barrier_load_cell_classification_config_v2.2.1.json`
- DB: `data/full_2011plus_metadata_only_refresh_2026-05-03.sqlite`
- Mode: strict machine execution with `shape_normalization_policy` applied before rule matching
- Live API: not used

## Result

v2.2.1 validates against the current 2011+ DB snapshot.

| Execution mode | Candidate tests | Classified | Unclassified | Result |
|---|---:|---:|---:|---|
| Raw `barriers.shape` exact match without alias layer | 1,137 | 1,127 | 10 | Expected v2.2.0 caveat reproduced |
| v2.2.1 shape-normalized strict execution | 1,137 | 1,137 | 0 | PASS |

All `expected_current_db_coverage_after_rules` top-level counts matched actual results.

## Classification Summary

Shape-normalized strict execution:

| Classification id | Tests | Channels | Force channels | Moment channels | Check |
|---|---:|---:|---:|---:|---|
| `legacy_4x9_us_ncap` | 112 | 4,032 | 4,032 | 0 | PASS |
| `high_res_8x16_128` | 2 | 768 | 256 | 512 | PASS |
| `partial_8x16_127_missing_one_force_channel` | 8 | 1,016 | 1,016 | 0 | PASS |
| `extended_height_10x16_160` | 48 | 13,184 | 7,680 | 5,504 | PASS |
| `advanced_11x16_128_active` | 96 | 22,784 | 12,288 | 10,496 | PASS |
| `advanced_11x16_176_full` | 283 | 136,400 | 49,808 | 86,592 | PASS |
| `side_pole_load_cell_8` | 588 | 4,701 | 4,701 | 0 | PASS |
| Total | 1,137 | 182,885 | 79,781 | 103,104 | PASS |

## Shape Normalization Audit

The 10 raw-shape alias cases are correctly closed by v2.2.1:

| Raw shape | Normalized key | Tests | Rule |
|---|---|---:|---|
| `8 X 16 LOAD CELL BARRIER` | `LOAD_CELL_BARRIER` | 7 | `advanced_11x16_128_active` |
| `OTHER` | `OTHER_LOAD_CELL_BARRIER_REVIEWED` | 1 | `extended_height_10x16_160` |
| `FLAT BARRIER` | `FLAT_BARRIER_LEGACY_LOAD_CELL` | 2 | `legacy_4x9_us_ncap` |

Test numbers:

- `8 X 16 LOAD CELL BARRIER`: `8066`, `8071`, `8077`, `8091`, `8100`, `8151`, `8155`
- `OTHER`: `8603`
- `FLAT BARRIER`: `9662`, `9989`

The `OTHER` alias remained conditional: it required high-resolution load-cell barrier evidence plus row/column occupancy matching `160` force channels, rows `2-11`, columns `1-16`.

## Mask Audit

Partial 8x16 wall:

- `7201`, `7203`, `7339`, `7347`, `7350`, `7358`, `7362`, `7370`
- missing expected force cell: `(row=2, col=16)`

Pole barrier mask cases:

- `11656`: missing pole indices `7`, `8`
- `14604`: missing pole indices `1`, `2`
- `14617`: duplicate pole index `8`

## Metadata Caveat

`legacy_4x9_us_ncap` does not include a `classification_status` field in `classification_rules`. The validator used the expected/default status `covered`, matching `expected_current_db_coverage_after_rules`. This is non-blocking for coverage, but adding `"classification_status": "covered"` to that rule would make the config metadata fully explicit.

## Verification

Local checks performed:

- parsed `docs/nhtsa_barrier_load_cell_classification_config_v2.2.1.json` as valid JSON
- applied `shape_normalization_policy` before rule matching
- followed `classification_strategy.rule_precedence`
- parsed attachment patterns from `channel_identifier_policy.attachment_parsers`
- compared actual rule counts/channels against `expected_current_db_coverage_after_rules.classification_summary_alias_assisted`
- confirmed raw exact-match mode still leaves the expected 10 alias cases

