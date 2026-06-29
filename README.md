# nhtsa_metadata

## Purpose

`nhtsa_metadata` is a metadata-only catalog database for 2011+ NHTSA Vehicle Crash Test Database
metadata. It preserves raw NHTSA source responses, normalizes important engineering filter domains,
and exposes query/filter APIs.

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
.venv\Scripts\python.exe -m ruff check src tests
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

## Metadata refresh v10 local runtime

After user approval on 2026-06-28, the local `.env` may point at the finalized 2011+ DB:

```text
NHTSA_METADATA_DATABASE_URL=sqlite:///D:/vscode/nhtsa_metadata/data/nhtsa_test_metadata_2011.sqlite
NHTSA_METADATA_ALLOW_LIVE=true
```

Run the local API/GUI:

```bash
uv run uvicorn nhtsa_metadata.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

Useful endpoints:

- `http://127.0.0.1:8000/metadata-refresh`
- `http://127.0.0.1:8000/api/metadata-refresh/v10/summary`
- `http://127.0.0.1:8000/api/tests?metadata_flag=live_summary_missing_v10`
- `http://127.0.0.1:8000/api/tests?metadata_flag=source_semantics_conflict_v10`
- `http://127.0.0.1:8000/api/filter-options`

When the v10 DB objects are present, `/api/tests`, `/api/tests/{test_no}`, and
`/api/filter-options` prefer the approved `metadata_refresh_v10_final` overlay read models while
preserving original source/canonical rows.

## Project Layout

```text
src/nhtsa_metadata/       Python package
tests/                    Unit and smoke tests
scripts/                  Local test and verification scripts
.harness/                 Codex harness entrypoint
.codex/                   Repo-local Codex operating rules
.skills/                  Repo-local reusable agent skills
.agent/                   Project metadata for agent workflows
.agents/skills/           Compatibility skill wrappers
docs/phase_reports/       Per-phase implementation reports
nhtsa_metadata_codex_work_orders/  Implementation work orders
```
