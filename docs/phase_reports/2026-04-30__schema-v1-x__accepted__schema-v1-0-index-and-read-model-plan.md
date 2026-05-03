# 2026-04-30 | Schema v1.x | ACCEPTED | Schema v1.0 Index and Read Model Plan

﻿# Schema v1.0 Index And Read Model Plan

## Decision

Schema v1.0 keeps SQLite indexes conservative and documents PostgreSQL/full-scale index candidates. No `payload_json` or `raw_row_json` whole-column index is allowed.

## Existing SQLite Index Policy

Use only bounded indexes needed by current API, rebuild, and audit paths:

- `tests(test_no)`
- `vehicles(test_id)` and `vehicles(test_no)`
- `barriers(test_id)` and `barriers(test_no)`
- `occupants(test_id)`
- `restraints(test_id)`
- `instrumentation_channels(test_id)` and `instrumentation_channels(test_no)`
- `media_assets(test_id)`
- `source_payloads(test_no)`, `source_payloads(endpoint_name)`, `source_payloads(payload_hash)`
- `source_payload_observations(source_payload_id)` via FK use
- `test_filter_summary(test_no)`
- `test_classification(test_no)`
- `asset_summary(test_no)`

## Full-Scale Before-Run Index Candidates

Apply only if a measured local query needs them before the approved full-scale run:

- `tests(test_date)`
- `tests(test_configuration_key)`
- `test_filter_summary(test_date)`
- `test_filter_summary(test_configuration_key)`
- `test_participants(test_id, participant_kind)`
- `occupants(test_id, vehicle_id, occupant_location_normalized)`
- `restraints(test_id, occupant_id)`
- `restraints(test_id, occupant_location_normalized)`
- `media_assets(test_id, asset_kind, asset_subtype)`
- `source_payloads(test_no, endpoint_name)`
- `source_payload_observations(test_no, endpoint_name)` if materialized in a later schema

## PostgreSQL Migration Candidates

When moving beyond SQLite, evaluate:

- `vehicles(make, model, model_year)`
- `instrumentation_channels(sensor_type)`
- `instrumentation_channels(sensor_attachment)`
- `instrumentation_channels(sensor_axis)`
- `instrumentation_channels(unit_raw)`
- `instrumentation_channels(test_id, curve_no)`
- `test_facets(facet_name, facet_value)`
- partial indexes for `media_assets(asset_kind='data_package')`

## Prohibited Indexes

- `payload_json` whole-column index
- `raw_row_json` whole-column index
- large text commentary whole-column index
- URL/hash/path indexes unless a specific lookup path is measured and approved

## Read-Model Promotion Policy

Promote to read model when all are true:

- repeated across multiple tests
- stable type and semantics
- user-facing filter or audit need exists
- derivable from raw/canonical tables
- not an identifier disguised as a dictionary field

Read-model fields retained in v1.0:

- test type/configuration/date
- vehicle make/model/model year
- participant kind
- barrier rigidity/shape
- occupant location
- restraint type/deployment
- instrumentation sensor type/location/attachment/axis/unit/status
- injury/deformation codes
- asset kind/subtype/data package subtype

Raw-only fields retained in v1.0:

- raw payload JSON
- raw row JSON
- source endpoint links and summary links
- media/package internals
- free text commentary
- low-support ambiguous fields

## Facet Coverage Policy

Required facets: 27.
Present in the 1500-test analysis: 26.
Missing: `dummy_type`.

`dummy_type` is an accepted warning because the observed pilot data does not contain stable non-null values. If stable non-null `dummy_type` values are later observed, the read model may add them as `test_facets(dummy_type, value)` without making absence a hard failure.
