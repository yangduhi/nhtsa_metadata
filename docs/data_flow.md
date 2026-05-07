# Data Flow

## Overview

The project data flow is raw-first and rebuildable:

```text
discover or load manifest
-> fetch endpoint payloads
-> store immutable source payloads
-> parse endpoint sections
-> map canonical entities
-> rebuild filter/read-model tables
-> run schema, endpoint, classification, and lineage validation
```

## Extract

Extraction is implemented by the NHTSA source package and catalog services:

- `sources/nhtsa_crash/endpoints.py` defines endpoint templates.
- `sources/nhtsa_crash/live_client.py` performs live calls only when explicitly
  allowed.
- `sources/nhtsa_crash/fixtures.py` provides fixture-only default verification.
- `services/catalog_builder.py` and `services/endpoint_completeness.py`
  coordinate manifest-driven collection and backfill.

## Transform

Canonical transformation is separated from source fetching:

- `sources/nhtsa_crash/parsers.py` and `normalization.py` normalize endpoint
  payload shapes and scalar values.
- `services/canonical_mapper.py` maps payload rows into canonical domain rows.
- `services/vehicle_filter_fields.py` promotes vehicle filter fields from
  vehicle raw payload aliases.
- `services/read_model_builder.py` rebuilds filter summaries, classifications,
  facets, and derived read models.

## Validate

Validation does not mutate source payloads:

- `services/schema_audit.py` checks scope, read-model, duplicate, and semantic
  audit rules.
- `services/endpoint_completeness.py` checks manifest and endpoint coverage.
- `services/classification_accounting.py` computes accounted/canonical and
  final disposition metrics.
- `services/classification_lineage.py` checks source-to-final-decision lineage
  fixtures.

## Load

Persistence is handled by DB/session services and service-level upserts:

- `db/models.py` defines raw, canonical, and read-model tables.
- `services/source_payload_service.py` stores source payloads and observations.
- `services/canonical_upsert.py` preserves canonical row lineage.
- `services/filter_db_materializer.py` creates the final GUI-facing
  filter-ready DB from an existing metadata DB without modifying the source DB.

## Final Materialized Output

Final filter-ready DB:

```text
data/full_2011plus_metadata_filter_ready_2026-05-04.sqlite
```

This DB is an ignored runtime artifact. It can be regenerated from the
committed materialization code and preserved input DB artifacts.
