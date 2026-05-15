# NHTSA Barrier Load-Cell Instrumentation Classification — Final v2.2.2

**Date:** 2026-05-03
**Status:** Final project configuration; shape-normalized strict execution PASS; all active rule statuses explicit
**DB:** `data/full_2011plus_metadata_only_refresh_2026-05-03.sqlite`
**Scope:** 2011+ metadata-only catalog, barrier-side load-cell instrumentation
**Live NHTSA API:** Not used for this metadata classification closure

---

## 1. Final conclusion

v2.2.2 is a metadata-explicitness patch over v2.2.1.

The validated v2.2.1 rule logic already closed the current DB universe when `shape_normalization_policy` was applied before rule matching:

```text
candidate tests = 1,137
classified      = 1,137
unclassified    = 0
```

The only remaining caveat was that `legacy_4x9_us_ncap` did not carry an explicit `classification_status` field. v2.2.2 adds:

```json
"classification_status": "covered"
```

to `legacy_4x9_us_ncap`.

No classification logic, alias condition, count, channel summary, mask policy, tensor policy, or rule precedence changed.

---

## 2. Delta from v2.2.1

| Area | v2.2.1 | v2.2.2 |
|---|---|---|
| Shape normalization | Explicit | Unchanged |
| Coverage | `1,137 / 1,137` | Unchanged |
| Raw exact-match caveat | 10 unclassified if shape normalization is not applied | Unchanged; non-compliant mode |
| `legacy_4x9_us_ncap.classification_status` | Missing; validator defaulted to `covered` | Explicitly set to `covered` |
| Validation metadata | PASS, with caveat | PASS, caveat removed |

---

## 3. Machine-execution contract

A strict classifier must execute in this order:

```text
1. Select barrier-side load-cell candidate universe.
2. Preserve raw barriers.shape as raw_barrier_shape.
3. Normalize raw_barrier_shape through shape_normalization_policy.
4. Emit normalized_barrier_shape_key.
5. Parse attachment pattern.
6. Derive row/column or pole-index occupancy.
7. Match classification_rules using shape_match.allowed_normalized_keys.
8. Validate force/moment counts and occupancy signature.
9. Emit classification_id, classification_status, masks, raw shape, normalized key, and alias audit fields.
```

Direct raw `barriers.shape` exact matching is **not** a valid v2.2.2 implementation mode.

---

## 4. Shape normalization policy

### 4.1 Raw preprocessing

```text
- trim whitespace
- uppercase
- collapse internal whitespace
- preserve raw value in output
```

Required output audit fields:

```text
raw_barrier_shape
normalized_barrier_shape_key
shape_alias_rule_id
shape_alias_confidence
shape_alias_evidence
shape_alias_is_conditional
```

### 4.2 Unconditional aliases

| Raw `barriers.shape` | Normalized key | Notes |
|---|---|---|
| `LOAD CELL BARRIER` | `LOAD_CELL_BARRIER` | Wall-family candidate |
| `8 X 16 + 6 LOAD CELL BARRIER` | `LOAD_CELL_BARRIER` | Wall-family candidate |
| `8 X 16 LOAD CELL BARRIER` | `LOAD_CELL_BARRIER` | Wall-family candidate; resolves 7 alias cases |
| `POLE` | `POLE` | Side pole load-cell barrier candidate |

Unconditional aliasing only normalizes the shape. Final assignment still requires attachment-pattern and occupancy validation.

### 4.3 Conditional aliases

#### `FLAT BARRIER` → legacy 4×9 load-cell wall only

`FLAT BARRIER` is generic and must **not** be globally aliased to load-cell wall. It is accepted only for the legacy 4×9 LCW occupancy signature.

Conditions:

```text
- sensor_type is LOAD CELL;
- attachment matches ^LOAD CELL (?P<row_letter>[A-D])(?P<col>[1-9])$;
- observed force channel count equals 36;
- row letters are A-D and columns are 1-9;
- no pole attachment pattern is present for the same barrier participant.
```

Observed current DB cases:

```text
9662, 9989
```

#### `OTHER` → reviewed high-resolution load-cell barrier only

`OTHER` is unsafe as a global alias. It is accepted only when independent text evidence and row/column occupancy both identify a known load-cell wall rule.

Conditions:

```text
- sensor_type is LOAD CELL;
- attachment matches ^LOAD CELL ROW (?P<row>\d+) COLUMN (?P<col>\d+)$;
- observed force channel count equals 160;
- observed row range is 2–11 and observed column range is 1–16;
- title/commentary/INSCOM or reviewed metadata contains load-cell-barrier evidence.
```

Observed current DB case:

```text
8603 → extended_height_10x16_160
```

---

## 5. Alias cases required for closure

| Raw shape | Count | Tests | Assigned rule | Evidence |
|---|---:|---|---|---|
| `8 X 16 LOAD CELL BARRIER` | 7 | `8066`, `8071`, `8077`, `8091`, `8100`, `8151`, `8155` | `advanced_11x16_128_active` | 128 force channels; active rows 4–11; columns 1–16 |
| `OTHER` | 1 | `8603` | `extended_height_10x16_160` | Reviewed metadata evidence plus 160 force channels; rows 2–11; columns 1–16 |
| `FLAT BARRIER` | 2 | `9662`, `9989` | `legacy_4x9_us_ncap` | `LOAD CELL A-D` / columns 1–9; 36 force channels |

These 10 cases explain the difference between raw-shape exact execution and shape-normalized execution.

---

## 6. Final classification summary

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

## 7. Final active rules

### 7.1 `legacy_4x9_us_ncap`

```text
family = frontal_or_flat_load_cell_wall
shape_match.allowed_normalized_keys = LOAD_CELL_BARRIER, FLAT_BARRIER_LEGACY_LOAD_CELL
attachment_pattern = ^LOAD CELL (?P<row_letter>[A-D])(?P<col>[1-9])$
rows = 4
cols = 9
nominal_force_count = 36
classification_status = covered
physical_size_mm = 2108.2 × 984.25
```

`FLAT_BARRIER_LEGACY_LOAD_CELL` is conditional and allowed only by the legacy 4×9 occupancy signature.

### 7.2 `high_res_8x16_128`

```text
family = frontal_or_flat_load_cell_wall
shape_match.allowed_normalized_keys = LOAD_CELL_BARRIER
attachment_pattern = ^LOAD CELL ROW (?P<row>\d+) COLUMN (?P<col>\d+)$
rows = 8
cols = 16
nominal_force_count = 128
classification_status = covered_with_geometry_caveat
```

The row-offset caveat remains. Report-specific geometry should be checked before physical interpretation.

### 7.3 `partial_8x16_127_missing_one_force_channel`

```text
base_configuration = high_res_8x16_128
shape_match.allowed_normalized_keys = LOAD_CELL_BARRIER
rows = 8
cols = 16
expected_force_count = 128
observed_force_count = 127
missing_force_cell = row 2, col 16
known tests = 7201, 7203, 7339, 7347, 7350, 7358, 7362, 7370
classification_status = covered_with_mask
required masks = physical_cell, active_channel, valid_Fx, missing_expected_channel, padding
```

This remains a mask-aware partial variant and should not be collapsed silently into complete 128-channel 8×16.

### 7.4 `extended_height_10x16_160`

```text
family = frontal_or_flat_load_cell_wall
shape_match.allowed_normalized_keys = LOAD_CELL_BARRIER, OTHER_LOAD_CELL_BARRIER_REVIEWED
attachment_pattern = ^LOAD CELL ROW (?P<row>\d+) COLUMN (?P<col>\d+)$
rows = 10
cols = 16
nominal_force_count = 160
observed row range = 2–11
observed col range = 1–16
classification_status = covered
```

`OTHER_LOAD_CELL_BARRIER_REVIEWED` is conditional and currently applies only to test `8603` under the documented evidence requirements.

### 7.5 `advanced_11x16_128_active`

```text
family = frontal_or_flat_load_cell_wall
shape_match.allowed_normalized_keys = LOAD_CELL_BARRIER
attachment_pattern = ^LOAD CELL ROW (?P<row>\d+) COLUMN (?P<col>\d+)$
physical_rows = 11
physical_cols = 16
active_force_count = 128
active rows observed = 4–11
columns observed = 1–16
classification_status = covered_with_active_cell_mask
required masks = physical_cell, active_channel, valid_Fx, inactive_physical_cell
```

This rule resolves the raw-shape alias group `8 X 16 LOAD CELL BARRIER`.

### 7.6 `advanced_11x16_176_full`

```text
family = frontal_or_flat_load_cell_wall
shape_match.allowed_normalized_keys = LOAD_CELL_BARRIER
attachment_pattern = ^LOAD CELL ROW (?P<row>\d+) COLUMN (?P<col>\d+)$
rows = 11
cols = 16
nominal_force_count = 176
moment_channels_optional = true
classification_status = covered
total channels may be 176 or 528 depending on moment availability
```

Do not infer `8×22` from force count 176 alone.

### 7.7 `side_pole_load_cell_8`

```text
family = side_pole_load_cell_barrier
shape_match.allowed_normalized_keys = POLE
attachment_patterns = ^LOAD CELL POLE (?P<pole_index>\d+)$, ^POLE$
legacy index source = INSCOM pattern LOAD CELL (?P<pole_index>\d+)
nominal_force_count = 8
observed_force_count_allowed = 6, 8, 9
classification_status = covered_with_mask
```

Known pole mask cases:

| Test | Observed force channels | Mask issue |
|---|---:|---|
| `11656` | 6 | missing pole indices 7, 8 |
| `14604` | 6 | missing pole indices 1, 2 |
| `14617` | 9 | duplicate pole index 8 |

---

## 8. Explicitly rejected assumptions

| Assumption | Final handling |
|---|---|
| Raw `barriers.shape` exact matching is sufficient | Rejected; normalize first |
| `OTHER` can be globally aliased to load-cell barrier | Rejected; conditional only |
| `FLAT BARRIER` can be globally aliased to load-cell barrier | Rejected; legacy 4×9 occupancy only |
| `force_count` alone determines wall geometry | Rejected |
| `176 = 8×22` | Rejected unless row/column extent or report geometry proves 8×22 |
| `Row 11 = auxiliary` | Rejected |
| Missing moment channels can be filled with zero for physics | Rejected; use `NaN` + masks |
| Raw `LOMA` parser is primary DB parser | Rejected for current DB |
| 4×9 size is `2250×1000 mm` | Replaced by `2108.2×984.25 mm` unless report-specific geometry says otherwise |

---

## 9. Validation checks

```text
- Apply shape_normalization_policy before classification rules.
- Strict shape-normalized execution must classify 1,137 / 1,137 current DB barrier-side load-cell tests.
- Strict raw barriers.shape exact matching without alias layer is expected to leave 10 known alias cases unclassified; using it for v2.2.2 is non-compliant.
- Every active classification_rules entry must include classification_status explicitly.
- Do not globally alias raw shape OTHER to LOAD_CELL_BARRIER.
- Do not globally alias raw shape FLAT BARRIER to LOAD_CELL_BARRIER.
- Every classified wall-grid test must emit an occupancy map.
- Every classified pole test must emit pole-index coverage plus duplicate/missing masks.
- Moment channel absence must remain NaN/masked for physical calculations; zero padding is allowed only for model input with masks.
- Raw LOMA-compatible names must not be required for DB primary classification.
- Inactive/external candidates wide_8x22_176 and large_lcw_288 must not be activated without row/column extent or report-specific evidence.
```

---

## 10. Files

- JSON config: `nhtsa_barrier_load_cell_classification_config_v2.2.2.json`
- Markdown final: `nhtsa_barrier_load_cell_classification_final_v2.2.2_2026-05-03.md`
