# Index Strategy

## SQLite V1

- Index lookup paths by `test_no`, endpoint name, payload hash, and fetched time.
- Keep natural unique constraints for `tests.test_no`, `instrumentation_channels(test_id, curve_no)`,
  and `media_assets(test_id, asset_kind, canonical_url_hash)`.
- Do not add a large whole-payload JSON index in v1.
- Use read-model tables for common filter/facet queries instead of scanning raw payload JSON.

## Query Surfaces

- `test_filter_summary` supports list/filter screens.
- `test_facets` supports facet option counts.
- `asset_summary` supports asset availability counts.
- `source_field_catalog` supports field coverage and unmapped-field review.
