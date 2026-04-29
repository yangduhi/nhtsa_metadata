# Filtering Contract

이 프로젝트의 canonical/read-model 대상은 `test_date >= 2011-01-01`인 NHTSA crash test metadata로 제한한다.
`modelYear`는 scope 판단 기준이 아니다.
`test_date` missing 또는 parse 실패 record는 기본적으로 canonical/read-model에서 제외한다.

Required facets:

- `test_type`
- `test_configuration`
- `vehicle_make`
- `vehicle_model`
- `model_year`
- `closing_speed_range`
- `impact_angle`
- `participant_kind`
- `barrier_rigidity`
- `barrier_shape`
- `occupant_location`
- `dummy_type`
- `restraint_type`
- `restraint_deployment`
- `sensor_type`
- `sensor_location`
- `sensor_attachment`
- `sensor_axis`
- `sensor_unit`
- `injury_metric_code`
- `injury_metric_range`
- `deformation_code`
- `asset_kind`
- `has_uds_or_tdms_package`

V1 compound filter semantics: a test matches when all requested conditions exist somewhere inside
the same test. Same occupant or same vehicle scoped filtering can be refined in a later version.

For occupant-scoped facets, read models should use normalized occupant slots rather than raw source
occupant observations.
