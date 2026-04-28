# nhtsa_metadata

## Purpose

`nhtsa_metadata` is a metadata-only catalog database for the NHTSA Vehicle Crash Test Database.
It preserves raw NHTSA source responses, normalizes important engineering filter domains, and
exposes query/filter APIs.

## Scope

- Python package: `nhtsa_metadata`
- FastAPI application skeleton
- SQLite/SQLAlchemy/Alembic foundation
- Fixture/mock based verification
- Raw/provenance, canonical, and read-model layers in later phases
- CLI and local verification scripts

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
harness scripts. Bounded live validation requires both `--allow-live` and
`NHTSA_METADATA_ALLOW_LIVE=true`.

## Project Layout

```text
src/nhtsa_metadata/       Python package
tests/                    Unit and smoke tests
scripts/                  Local test and verification scripts
.harness/                 Codex harness entrypoint
docs/phase_reports/       Per-phase implementation reports
nhtsa_metadata_codex_work_orders/  Implementation work orders
```
