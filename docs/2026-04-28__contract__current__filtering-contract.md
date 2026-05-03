# 2026-04-28 | Contract | CURRENT | Filtering Contract

﻿# Filtering Contract

이 프로젝트의 canonical/read-model 대상은 `test_date >= 2011-01-01`인 NHTSA crash test metadata로 제한한다.
`modelYear`는 scope 판단 기준이 아니다.
`test_date` missing 또는 parse 실패 record는 기본적으로 canonical/read-model에서 제외한다.

## Required Facets

Schema v1.0 required facets:

- `test_type`
- `test_configuration`
- `test_configuration_key`
- `test_family`
- `classification_status`
- `vehicle_make`
- `vehicle_model`
- `model_year`
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
- `channel_status`
- `data_status`
- `injury_metric_code`
- `deformation_code`
- `asset_kind`
- `asset_subtype`
- `data_package_subtype`

Current accepted coverage is 26/27. `dummy_type` may be absent when no stable non-null value is observed; this is a warning, not a hard failure.

## Filter Semantics

V1 compound filter semantics: a test matches when all requested conditions exist somewhere inside the same test.

For occupant-scoped facets, read models use normalized occupant slots rather than raw source occupant observations.

For data packages, filters use URL/metadata registry fields only. Package contents are outside v1.0.

## Read Model Policy

`test_filter_summary`, `test_classification`, `test_facets`, and `asset_summary` are rebuildable derivatives. They must not contain pre-2011 tests or missing/parse-failed test dates.
