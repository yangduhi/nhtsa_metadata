# 2026-04-28 | Contract | CURRENT | Field Coverage Contract

﻿# Field Coverage Contract

Field coverage is a raw/provenance audit surface for Schema v1.0.

## Scope

- Coverage is computed from stored `source_payloads` and `source_field_catalog`.
- Field paths are normalized with wildcard array indexes, for example `$.results[0].vehicleNo` becomes `$.results[*].vehicleNo`.
- Coverage is report data and does not replace raw payloads.

## Mapping Statuses

- `mapped`
- `extra_json`
- `unmapped`
- `ignored_by_policy`
- `conflict`

## Minimum Report Fields

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

## Schema v1.0 Promotion Rules

Promote only when semantics are stable, repeated, and useful for canonical/read-model filtering. Do not promote identifiers, raw URLs, hashes, paths, large commentary, file internals, or numeric measurements as dictionary values.

## Backlog Classification

- P0/P1 schema recommendations block full-scale readiness.
- P2 dictionary/index/facet candidates require explicit v1.0 decision.
- P3 cleanup/documentation items do not block.
- `dummy_type` missing coverage is accepted warning while stable non-null values are absent.
