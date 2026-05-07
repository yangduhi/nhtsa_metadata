# nhtsa_metadata

## Purpose

`nhtsa_metadata` is a metadata-only catalog database for 2011+ NHTSA Vehicle Crash Test Database
metadata. It preserves raw NHTSA source responses, normalizes important engineering filter domains,
and exposes query/filter APIs.

The project is closed for first delivery as a metadata DB project. Downstream
GUI design and productization are handled outside this repository.

## Scope

- Python package: `nhtsa_metadata`
- FastAPI application skeleton
- SQLite/SQLAlchemy/Alembic foundation
- Fixture/mock based verification
- Raw/provenance, canonical, and read-model layers
- Canonical/read-model scope fixed to `test_date >= 2011-01-01`
- Bounded manual live validation through manifest-driven commands only

## Not in Scope

- UI
- Download execution
- Queue/progress APIs
- Waveform parsing
- TDMS/UDS/ABF/ISO parsing
- Production crawler
- Automatic live NHTSA API calls in default verification

## Setup

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Copy `.env.example` to `.env` only when local overrides are needed. Keep
`NHTSA_METADATA_ALLOW_LIVE=false` for default development.

## Verification

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m mypy src\nhtsa_metadata
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
powershell -ExecutionPolicy Bypass -File .harness\run.ps1
```

Default verification must not call live NHTSA services.

## Manual Live Validation

Manual live validation remains disabled by default and is not used by tests, verify scripts, or
harness scripts. Bounded live validation requires `--source live`, `--allow-live`, and
`NHTSA_METADATA_ALLOW_LIVE=true`.

The local reference DB at `D:\vscode\pulse_analysis\data\db\nhtsa_data.db` may be used only as a
bounded manifest seed. It is not the source of truth for canonical metadata.

## Project Layout

```text
src/nhtsa_metadata/              Python package
src/nhtsa_metadata/sources/      NHTSA endpoint definitions, clients, parsers
src/nhtsa_metadata/services/     Catalog, ingestion, schema, classification, read-model services
src/nhtsa_metadata/db/           SQLAlchemy models, sessions, Alembic helpers
src/nhtsa_metadata/api/          FastAPI read/query surface
tests/                           Unit, integration, and regression tests
scripts/                         Local verification scripts
.harness/                        Codex harness entrypoint
docs/                            Architecture, contracts, reports, and handoff docs
docs/phase_reports/              Per-phase implementation reports
nhtsa_metadata_codex_work_orders/ Implementation work orders
```

## Architecture and Handoff Docs

- `docs/architecture.md`: package/layer overview
- `docs/data_flow.md`: extract, transform, validate, load flow
- `docs/schema.md`: handoff schema summary
- `docs/baseline_report.md`: pre-refactoring output baseline
- `docs/refactoring_audit.md`: post-delivery refactoring findings
- `docs/refactoring_plan.md`: bounded refactoring plan
- `docs/refactoring_report.md`: refactoring closeout
- `docs/validation_report.md`: validation and regression evidence

## Final Output DB

Final filter-ready runtime artifact:

```text
data/full_2011plus_metadata_filter_ready_2026-05-04.sqlite
```

This file is intentionally ignored under `data/`. The committed code, fixtures,
migrations, and reports define how to regenerate and validate it.
