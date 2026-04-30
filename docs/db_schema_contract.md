# DB Schema Contract

Schema v1.0 is the contract for a 2011+ NHTSA crash test metadata-only database.

이 프로젝트의 canonical/read-model 대상은 `test_date >= 2011-01-01`인 NHTSA crash test metadata로 제한한다.
`modelYear`는 scope 판단 기준이 아니다.
`test_date` missing 또는 parse 실패 record는 기본적으로 canonical/read-model에서 제외한다.

## Required Layers

The schema must include:

- raw/provenance tables for endpoint, payload, observation, section, field coverage, conflict, and canonical row source tracking
- canonical tables for tests, participants, vehicles, barriers, occupants, restraints, instrumentation, injury metrics, deformation, intrusion, media assets, and code values
- read-model / derived tables for filter summary, facets, asset summary, test classification, and coverage snapshots

Raw payloads are immutable. Canonical/read-model tables are rebuildable derivatives.

## Discovery Provenance Contract

Schema v1.2 adds a governance layer for full-manifest authority:

- `discovery_runs` records manifest discovery, reference-seed validation, and merge runs.
- `discovery_manifest_rows` records why each `test_no` was included or excluded, including
  `seed_source`, live/reference presence, validation status, authority status, and row hash.
- `discovery_authority_decisions` records the selected discovery authority and supporting
  counts.

The reference DB may be used only as a discovery seed. A reference-only row must not become
`authoritative_included` unless an official live discovery-validation endpoint confirms the
test number and an in-scope parseable `test_date`.

Allowed discovery-validation endpoints are limited to:

- `test_summary`
- `test_detail`
- `metadata_export`

This validation is not endpoint matrix detail collect. It must not call vehicle, occupant,
restraint, intrusion, instrumentation, multimedia, or document detail endpoints.

## Canonical Duplicate Hardening Rules

- `occupants` represent normalized occupant slots, not raw source observations.
- `restraints` represent occupant-context restraint assignments.
- Each occupant-specific restraint row must keep `occupant_id` or `restraint_subject_kind`, `restraint_subject_semantic_key`, and `restraint_subject_semantic_hash`.
- `restraints` use semantic identity over test, restraint subject, and restraint system fields.
- `barriers` dedupe normalized barrier identity across `metadata_export` and detail endpoints when they describe the same barrier.
- `instrumentation_channels` are unique by `(test_id, curve_no)`.
- `media_assets` dedupe by `(test_id, asset_kind, canonical_url_hash)` and never download files.
- `schema audit` must report duplicate summaries for vehicles, test participants, barriers, occupants, restraints, instrumentation channels, and media assets.
- `schema audit` must report semantic cardinality for occupant slots, restraint assignments, and barriers.

## code_values Contract

`code_values` is a derived dictionary registry, not source of truth. It must be rebuildable from canonical/read-model tables.

Allowed v1.0 code systems:

- `sensor_type`
- `sensor_attachment`
- `sensor_axis`
- `data_measurement_unit`
- `data_status`
- `channel_status`
- `occupant_location`
- `occupant_type`
- `restraint_type`
- `restraint_deployment`
- `barrier_rigidity`
- `barrier_shape`
- `asset_kind`
- `asset_subtype`
- `test_configuration_key`
- `classification_status`
- `participant_kind`

Identifiers and numeric measurements must not be dictionary/code value systems:

- `testNo`, `vehicleNo`, `curveNo`, row ids
- URL/hash/path fields
- `numberofFirstPoint`, `numberofLastPoint`, `timeIncrement`
- speed, weight, length, width, HIC, load, and other numeric measurement values

## Index Contract

Allowed by policy:

- targeted FK, unique-key, and filter-path indexes
- measured PostgreSQL indexes after full-scale analysis

Forbidden:

- whole-column `payload_json` index
- whole-column `raw_row_json` index
- broad commentary/text indexes without measured query need

## Facet Contract

Required facets are listed in `docs/filtering_contract.md`.

`dummy_type` is accepted as a warning when stable non-null values are absent. If stable non-null values are observed later, they can be emitted to `test_facets`; absence remains non-blocking.

## Conflict Contract

`source_conflicts` P0/P1 blocks full-scale readiness until resolved. Benign alias and numeric rounding differences are accepted P3 classes when policy/tolerance applies.
