# Field Coverage Contract

Mapping statuses:

- `mapped`
- `mapped_to_extra_json`
- `unmapped`
- `ignored_by_policy`
- `conflict`

Minimum report columns:

- `endpoint_name`
- `section_name`
- `field_path`
- `observed_type`
- `seen_count`
- `non_null_count`
- `mapping_status`
- `mapped_table`
- `mapped_column`
- `example_values`

Field paths are normalized with wildcard array indexes for coverage aggregation, for example
`$.results[0].vehicleNo` is reported as `$.results[*].vehicleNo`.
