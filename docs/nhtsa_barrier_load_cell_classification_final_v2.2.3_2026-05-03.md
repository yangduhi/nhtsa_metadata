# NHTSA Barrier Load-Cell Instrumentation Classification - Final v2.2.3

**Date:** 2026-05-03
**Status:** Final project configuration; shape-normalized strict execution PASS; Stage L DB read-model integration contract included
**DB:** `data/full_2011plus_metadata_only_refresh_2026-05-03.sqlite`
**Scope:** 2011+ metadata-only catalog, barrier-side load-cell instrumentation
**Live NHTSA API:** Not used for this metadata classification closure

---

## 1. Final conclusion

v2.2.3 is a Stage L integration-contract update over v2.2.2.

The classification rules, rule precedence, shape normalization behavior, candidate counts, channel counts, and coverage are unchanged from v2.2.2:

```text
candidate tests = 1,137
classified      = 1,137
unclassified    = 0
total channels  = 182,885
force channels  = 79,781
moment channels = 103,104
```

The new v2.2.3 content makes two implementation contracts explicit:

```text
1. DB derived read-model integration contract
2. unit-only quantity inference policy
```

This is metadata-level classification plus DB evidence-lineage/read-model closure. Waveform parsing, per-test NCAP PDF datasheet geometry validation, and report-specific physical orientation validation remain out of scope.

---

## 2. Delta from v2.2.2

| Area | v2.2.2 | v2.2.3 |
|---|---|---|
| Classification rules | Final and explicit | Unchanged |
| Shape normalization | Explicit | Unchanged |
| Coverage | `1,137 / 1,137` | Unchanged |
| Quantity fallback | Used by validator, not fully surfaced as a top-level contract | Explicit `quantity_inference_policy` |
| DB integration | Classification closure only | Derived read-model contract for DB reflection |
| Read-model tables | Not specified | `barrier_load_cell_classification`, `barrier_load_cell_channel_map` |
| Filter summary reflection | Not specified | load-cell barrier summary fields specified |

---

## 3. Final execution pipeline

A strict v2.2.3 classifier must execute in this order:

```text
raw channel/barrier metadata
-> quantity_inference_policy
-> shape_normalization_policy
-> attachment parsing
-> occupancy/mask construction
-> rule precedence
-> classification output
-> DB read-model reflection
```

Direct raw `barriers.shape` exact matching is not a valid v2.2.3 implementation mode.

---

## 4. Quantity inference policy

Stage L confirmed that quantity must be inferred from units when `YTYPE` is missing:

| Raw fields | Inferred quantity | Required for closure |
|---|---|---|
| `YTYPE = null`, `YUNITSD = NEWTONS` | `FORCE` | yes |
| `YTYPE = null`, `YUNITSD = NEWTON-METERS` | `MOMENT` | yes |

This fallback is applied before shape normalization and attachment parsing. Without it, full DB read-only validation cannot reliably reproduce `1,137 / 1,137` closure.

Required audit output:

```text
raw_YTYPE
raw_YUNITSD
raw_unit_raw
inferred_quantity
quantity_inference_rule_id
quantity_inference_confidence
```

---

## 5. DB read-model integration contract

v2.2.3 defines two derived tables. They are rebuildable read-model/evidence-lineage surfaces, not new sources of truth.

### 5.1 `barrier_load_cell_classification`

Grain: one row per classified barrier load-cell test/configuration.

Minimum required fields include:

```text
test_no
classification_id
classification_family
classification_status
config_version
raw_barrier_shapes_json
normalized_barrier_shape_key
shape_alias_rule_id
shape_alias_is_conditional
rows_observed
cols_observed
row_range_raw_json
col_range_raw_json
force_channel_count
moment_channel_count
total_channel_count
missing_expected_channels_json
duplicate_channels_json
mask_summary_json
evidence_json
created_at
```

### 5.2 `barrier_load_cell_channel_map`

Grain: one row per source instrumentation channel mapped into a barrier load-cell classification slot.

Minimum required fields include:

```text
test_no
curve_no
classification_id
config_version
source_payload_id
source_row_hash
sensor_attachment
sensor_axis
raw_YTYPE
raw_YUNITSD
unit_raw
inferred_quantity
quantity_inference_rule_id
row_raw
col_raw
pole_index_raw
channel_role
physical_cell
active_channel
valid_force
valid_Fx
valid_My
valid_Mz
missing_expected_channel
duplicate_channel
padding
data_status
channel_status
```

### 5.3 `test_filter_summary` reflection

The following derived fields are part of the integration contract:

```text
load_cell_barrier_classification_ids_json
load_cell_barrier_families_json
load_cell_barrier_config_version
load_cell_barrier_channel_count
load_cell_barrier_force_channel_count
load_cell_barrier_moment_channel_count
```

`has_load_cell_barrier` policy:

```text
- If barrier_load_cell_classification rows exist, use classifier output.
- If classification rows do not exist in an older DB snapshot, fall back to the existing shape/commentary detector.
- The fallback must not override classifier output.
```

---

## 6. Shape normalization closure

The v2.2.2 shape-normalization closure remains unchanged.

| Raw shape | Normalized key | Tests | Assigned rule |
|---|---|---:|---|
| `8 X 16 LOAD CELL BARRIER` | `LOAD_CELL_BARRIER` | 7 | `advanced_11x16_128_active` |
| `OTHER` | `OTHER_LOAD_CELL_BARRIER_REVIEWED` | 1 | `extended_height_10x16_160` |
| `FLAT BARRIER` | `FLAT_BARRIER_LEGACY_LOAD_CELL` | 2 | `legacy_4x9_us_ncap` |

`OTHER` remains conditional and must not be globally aliased.

---

## 7. Final classification summary

| Classification id | Tests | Channels | Force channels | Moment channels | Status |
|---|---:|---:|---:|---:|---|
| `legacy_4x9_us_ncap` | 112 | 4,032 | 4,032 | 0 | covered |
| `high_res_8x16_128` | 2 | 768 | 256 | 512 | covered_with_geometry_caveat |
| `partial_8x16_127_missing_one_force_channel` | 8 | 1,016 | 1,016 | 0 | covered_with_mask |
| `extended_height_10x16_160` | 48 | 13,184 | 7,680 | 5,504 | covered |
| `advanced_11x16_128_active` | 96 | 22,784 | 12,288 | 10,496 | covered_with_active_cell_mask |
| `advanced_11x16_176_full` | 283 | 136,400 | 49,808 | 86,592 | covered |
| `side_pole_load_cell_8` | 588 | 4,701 | 4,701 | 0 | covered_with_mask |
| **Total** | **1,137** | **182,885** | **79,781** | **103,104** | **covered** |

---

## 8. Final status

```text
Stage K:
classification rule gap identified

Stage K / v2.2.0-v2.2.2:
partial 8x16, pole, shape alias, explicit status caveat resolved

Stage L / v2.2.3:
DB schema reflection and per-channel evidence surface integration contract added
```

The current DB still contains no raw `LOMA` strings. Primary classification remains based on:

```text
SENTYPD
SENATTD
AXISD
YTYPE
YUNITSD
INSCOM
sensor_attachment
sensor_axis
unit_raw
barriers.shape
```

Legacy v2.1.0 assumptions are rejected or moved behind classification:

```text
LOMA substring parsing as primary DB parser
force-count-only classification
Row 11 auxiliary assumption
fixed tensor as universal NHTSA standard
```
