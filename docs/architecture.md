# Architecture

## Purpose

`nhtsa_metadata` is a metadata-only catalog for 2011+ NHTSA crash test records.
It preserves raw endpoint responses, builds canonical domain rows, and then
builds read-model tables for filtering and audit.

## Runtime Layers

```text
NHTSA endpoint or fixture payload
-> source client
-> raw/provenance persistence
-> canonical mapping
-> read-model rebuild
-> schema/accounting/audit reports
```

## Package Map

| Package | Responsibility |
|---|---|
| `nhtsa_metadata.config` | environment-driven settings |
| `nhtsa_metadata.constants` | default settings constants |
| `nhtsa_metadata.sources.nhtsa_crash` | endpoint definitions, clients, parsers, fixture clients, normalization |
| `nhtsa_metadata.db` | SQLAlchemy models, session setup, Alembic helpers |
| `nhtsa_metadata.services` | catalog, ingestion, canonical mapping, classification, read-model, schema, and reporting services |
| `nhtsa_metadata.api` | FastAPI read/query surface |
| `nhtsa_metadata.cli` | Typer command entrypoint that coordinates services |

## Source Boundary

Raw NHTSA payloads are the source of truth. Canonical and read-model tables are
rebuildable derivatives. `modelYear` is metadata, not a scope criterion.
Canonical/read-model scope is `test_date >= 2011-01-01`.

## Refactoring Boundary

The post-delivery refactoring keeps the existing architecture and avoids broad
module churn. The first implementation pass separates the filter-ready DB
materializer into orchestration, vehicle-field promotion, and report-building
helpers:

| Module | Responsibility |
|---|---|
| `services/filter_db_materializer.py` | copy source DB, ensure schema, rebuild read models, commit materialized DB |
| `services/vehicle_filter_fields.py` | promote vehicle spec filter fields from raw vehicle payload aliases |
| `services/filter_db_reports.py` | build materialized read-model summary payloads |

## Invariants

- Default tests and verification do not call live NHTSA APIs.
- Raw/source payload data is not rewritten by refactoring.
- Final DB output table names, column names, and accepted accounting metrics are
  preserved.
- `data/` runtime artifacts remain ignored by git.
