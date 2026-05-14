# nhtsa_metadata

## Purpose

`nhtsa_metadata` is the local DB and GUI-facing backend for 2011+ NHTSA Vehicle Crash Test Database
metadata. It preserves raw NHTSA source responses, normalizes important engineering filter domains,
exposes query/filter APIs, and provides controlled DB management and asset-download workflows for a
GUI.

The current product scope is intentionally narrow: build the metadata DB, manage local DB files, and
allow a GUI to download selected DB-registered assets. Historical schema research, pilot reports, and
classification experiments are retained only as operations/validation references unless promoted into
that product surface.

## Scope

- Python package: `nhtsa_metadata`
- FastAPI GUI-facing query, DB-status, and download-control API
- SQLite/SQLAlchemy/Alembic foundation
- Fixture/mock based verification
- Raw/provenance, canonical, and read-model layers
- Canonical/read-model scope fixed to `test_date >= 2011-01-01`
- Bounded manual live validation through manifest-driven commands only
- DB management commands for local SQLite status, backup, and maintenance
- Controlled asset-download queue based only on `media_assets` records already stored in the DB

## Not in Scope

- Full downstream GUI product implementation beyond the local asset console served by this API
- Unbounded or crawler-style download execution
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

## DB Management and GUI Downloads

The FastAPI app serves a local asset console at `/` and static assets under `/static/*`.
Run it against the configured SQLite baseline with:

```powershell
.venv\Scripts\python.exe -m uvicorn nhtsa_metadata.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/` to search DB-registered assets, queue selected downloads,
and review download jobs. The console uses the same API endpoints listed below.

The product CLI/API surface is centered on these local operations:

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli db status
.venv\Scripts\python.exe -m nhtsa_metadata.cli db backup --output data\backup.sqlite
.venv\Scripts\python.exe -m nhtsa_metadata.cli db vacuum
.venv\Scripts\python.exe -m nhtsa_metadata.cli download list-assets
.venv\Scripts\python.exe -m nhtsa_metadata.cli download enqueue --media-asset-id 1
```

Download jobs must be created from DB `media_assets` rows. Downloaded files are runtime artifacts and
belong in the configured download directory, not in tracked source files. Default verification uses
fixtures/mocks and must not perform live API calls or real downloads.

## Project Layout

```text
src/nhtsa_metadata/              Python package
src/nhtsa_metadata/sources/      NHTSA endpoint definitions, clients, parsers
src/nhtsa_metadata/services/     Catalog, ingestion, schema, classification, read-model services
src/nhtsa_metadata/db/           SQLAlchemy models, sessions, Alembic helpers
src/nhtsa_metadata/api/          FastAPI read/query surface and local asset-console static UI
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
- `docs/db_baseline.md`: current local keeper DB and data archive policy
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
migrations, and reports define how to regenerate and validate it. See
`docs/db_baseline.md` for keeper selection and archived non-keeper artifacts.

## CLI Surface

Product commands are intentionally small:

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli db status
.venv\Scripts\python.exe -m nhtsa_metadata.cli download list-assets
.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog materialize-filter-db --help
```

Operational/reporting commands are available under `ops`, and historical schema/research commands are under `legacy`. Backward-compatible top-level aliases for `coverage`, `scale`, and `schema` still execute but are hidden from top-level help.
