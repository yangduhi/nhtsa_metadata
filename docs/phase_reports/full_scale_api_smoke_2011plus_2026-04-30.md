# Full-Scale API Smoke 2011+

## Conclusion
- result: pass
- live_api_required: false

## Checks

| check | result | evidence |
|---|---|---|
| basic DB open | pass | `data\full_2011plus_metadata_only_stage_d_2026-04-30.sqlite` |
| table count | pass | `30` |
| sample test lookup | pass | `3891` |
| endpoint observation lookup | pass | `(1, 1, 200)` |
| source payload lookup | pass | `(1, 7201, 'test_summary', '3d918ab1c1cd1ab80714e8abd0d1befc5b98311b854e3786abb053ffe0f34e4c')` |
| classification lookup | pass | `db=(7201, 'frontal_barrier', 'classified'), v1.4_json=3891` |
| canonical lineage lookup | pass | `('vehicles', 1, 2)` |
| code_values lookup | pass | `('asset_kind', 'data_package', 19222)` |
| live API required | pass | `false` |
