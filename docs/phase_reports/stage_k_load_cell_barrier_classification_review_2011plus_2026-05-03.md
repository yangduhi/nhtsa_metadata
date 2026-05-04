# 2026-05-03 | Stage K | REVIEW | Load Cell Barrier Classification

## Scope

- Data source: `data/full_2011plus_metadata_only_refresh_2026-05-03.sqlite`
- Scope rule: in-repo 2011+ metadata-only catalog; no live NHTSA API calls.
- Target: barrier-side load-cell instrumentation represented in `instrumentation_channels`.
- Excluded from barrier classification: dummy/body load cells such as neck, femur, lumbar spine, abdomen, and face load cells where `barriers` has no barrier participant.

## DB Facts

- `tests`: 3,900
- `barriers`: 1,634
- `instrumentation_channels`: 471,566
- `sensor_type = 'LOAD CELL'`: 278,524 channels
- Raw `LOMA` string occurrence in current DB: 0

The current DB does not store ISO-MME/LOMA-style names such as `00LOMA110100FO1P`. The usable DB fields are `SENTYPD`, `SENATTD`, `AXISD`, `YTYPE`, `YUNITSD`, `INSCOM`, and canonical columns such as `sensor_attachment`, `sensor_axis`, and `unit_raw`. For this DB, LOMA-compatible naming would need to be generated from parsed row/column/cell metadata rather than parsed directly from a stored channel name.

## Barrier Load-Cell Families Observed

| Family | DB attachment pattern | Distinct tests | Channels | Barrier shape | Notes |
|---|---:|---:|---:|---|---|
| Legacy flat wall | `LOAD CELL A1` ... `LOAD CELL D9` | 112 | 4,032 | `LOAD CELL BARRIER` | 4 x 9, 36 force channels/test |
| Row/column load-cell wall | `LOAD CELL ROW n COLUMN m` | 437 | 174,152 | `LOAD CELL BARRIER` or `8 X 16 + 6 LOAD CELL BARRIER` | 8x16, 10x16, 11x16 variants with force and sometimes moment channels |
| Pole load-cell barrier | `LOAD CELL POLE n` or `POLE` | 588 | 4,701 | `POLE` | Not covered by the submitted candidate wall-grid configurations |

`FACE LOAD CELL ...` appears in 3 sled-with-body tests and has no barrier row; it is not counted as a barrier load-cell configuration.

## Submitted Candidate Coverage

| Candidate id | Matched tests | Status | Evidence rule used |
|---|---:|---|---|
| `legacy_4x9_us_ncap` | 112 | covered | `LOAD CELL A-D`, columns 1-9, 36 force channels |
| `high_res_8x16_128` | 2 | covered with row-offset caveat | 128 force channels, 8 rows x 16 cols, observed row range 3-10 |
| `advanced_11x16_128_active` | 96 | covered | 128 force channels, active rows 4-11, cols 1-16 |
| `advanced_11x16_176_full` | 283 | covered | 176 force channels, rows 1-11, cols 1-16 |
| `advanced_11x16_176_full` with moments | included above | covered | total channels may be 176 or 528 depending on whether `MY/MZ` moment channels are present |
| `wide_8x22_176` | 0 | not observed in current DB | no current 8 x 22 row/column family found |
| `ltv_10x16_160` | 48 | covered | 160 force channels, rows 2-11, cols 1-16 |
| `large_lcw_288` | 0 | not observed in current DB | no current force-count 288 LCW family found |

## Gaps

### Gap 1: partial 8x16 wall, 127 observed force channels

Eight tests have an `8 x 16` load-cell barrier with one missing force channel:

- test numbers: `7201`, `7203`, `7339`, `7347`, `7350`, `7358`, `7362`, `7370`
- observed force channels: 127
- observed rows: 2-9
- observed columns: 1-16
- missing cell in all eight: `(row=2, col=16)`
- barrier shape: `8 X 16 + 6 LOAD CELL BARRIER`

Exact `force_count = 128` matching leaves these unclassified. They should be treated as `high_res_8x16_128` or a distinct `partial_8x16_127_missing_one_force_channel` variant only if the tensor policy carries `valid_Fx`, `physical_cell`, and `active_channel` masks.

### Gap 2: pole load-cell barriers

There are 588 pole barrier tests with load-cell force channels:

- 585 tests have 8 force channels.
- 2 tests have 6 force channels: `11656`, `14604`.
- 1 test has 9 force channels due to duplicate pole 8 channel: `14617`.
- barrier shape: `POLE`
- observed attachment forms: `LOAD CELL POLE 1` ... `LOAD CELL POLE 8`, and older `POLE` rows where `INSCOM` carries `LOAD CELL 1` ... `LOAD CELL 8`.

These are real barrier load-cell measurements, but they do not fit any submitted grid candidate (`4x9`, `8x16`, `10x16`, `11x16`, `8x22`, or 288 LCW). A separate candidate is required if pole barriers are in scope.

## Recommended Rule Delta

Add a wall partial rule:

```json
{
  "id": "partial_8x16_127_missing_one_force_channel",
  "base_configuration": "high_res_8x16_128",
  "expected_force_count": 128,
  "observed_force_count": 127,
  "rows": 8,
  "cols": 16,
  "missing_force_cells_allowed": true,
  "required_masks": ["valid_Fx", "physical_cell", "active_channel", "padding"],
  "source_status": "dataset_observed_missing_channel_variant"
}
```

Add a pole barrier rule:

```json
{
  "id": "side_pole_load_cell_8",
  "barrier_shape": "POLE",
  "nominal_force_count": 8,
  "observed_force_count_allowed": [6, 8, 9],
  "attachment_patterns": ["^LOAD CELL POLE \\\\d+$", "^POLE$"],
  "quantity": "FORCE",
  "source_status": "dataset_inferred_unless_report_verified"
}
```

## Conclusion

The submitted candidate list classifies the main flat/load-cell-wall families, but it does not classify every barrier load-cell measurement in the DB as-is.

- Flat/load-cell wall only: 541 of 549 tests are exact-covered; the remaining 8 require a partial 8x16 missing-channel rule or explicit mask-aware assignment to `high_res_8x16_128`.
- All barrier load-cell measurements including pole barriers: 541 of 1,137 tests are exact-covered; 596 tests remain outside the submitted candidate set.
- LOMA naming cannot be validated directly from current DB strings because no `LOMA` channel names are stored.

## Verification Commands

Executed with the repo virtual environment and no live API calls:

- SQLite introspection of `tests`, `barriers`, and `instrumentation_channels`
- attachment-pattern scan for `LOAD CELL A-D`, `LOAD CELL ROW n COLUMN m`, `LOAD CELL POLE n`, and `POLE`
- per-test force/moment count grouping using raw `YTYPE/YUNITSD` plus canonical `unit_raw`

