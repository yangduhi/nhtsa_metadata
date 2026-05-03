# Stage K Vehicle Filter Promotion Result

## Scope

This change promotes only the requested filter surfaces:

1. vehicle specification fields on `vehicles`
2. vehicle specification range fields and `has_load_cell_barrier` on `test_filter_summary`

No production data, raw source payload data, classifier logic, or canonical test
taxonomy was changed.

## Vehicles Promotion

The canonical `vehicles` table now supports these additional fields:

- `body_type`
- `curb_weight_raw` / `curb_weight`
- `vehicle_length_raw` / `vehicle_length`
- `vehicle_width_raw` / `vehicle_width`
- `wheelbase_raw` / `wheelbase`
- `vax_crush_distance_raw` / `vax_crush_distance`

The mapper reads both API-style fields and `metadata_export.VEHICLE` aliases:

- `BODYD`
- `CURBWT`
- `VEHLEN`
- `VEHWID`
- `WHLBAS`
- `CRHDST`
- `vehicleLength`
- `vehicleWidth`
- `vaxCrushDistance`

## Filter Summary Promotion

`test_filter_summary` now records test-level min/max ranges for:

- `vehicle_test_weight`
- `curb_weight`
- `vehicle_length`
- `vehicle_width`
- `wheelbase`
- `vax_crush_distance`

The summary also records `has_load_cell_barrier`, derived from canonical barrier
shape and preserved raw barrier shape/commentary text. This is a barrier-target
filter and is separate from instrumentation load-cell sensor channels.

## API Surface

`/api/tests` can now filter by the promoted numeric ranges and by
`has_load_cell_barrier`. Range filters use overlap semantics against the
test-level min/max range.

`/api/tests/{test_no}` now includes the promoted vehicle fields in each vehicle
row.

## Validation

- `pytest tests\test_db_migrations.py tests\test_catalog_builder_fixture.py tests\test_api_queries.py -q`: passed
- `ruff check ...`: initial failure for two long lines; fixed before final validation
- `ruff check .`: passed
- `mypy src\nhtsa_metadata`: passed
- `pytest -q`: passed, 131 passed, 2 existing `TestFilterSummary` collection warnings
- `powershell -ExecutionPolicy Bypass -File scripts\verify.ps1`: passed
- `powershell -ExecutionPolicy Bypass -File .harness\run.ps1`: passed

## Remaining Notes

The range summary intentionally represents any vehicle in the test. If future UI
semantics require subject-vehicle-only compound filtering, add explicit
subject-vehicle summary fields rather than changing the current range semantics.
