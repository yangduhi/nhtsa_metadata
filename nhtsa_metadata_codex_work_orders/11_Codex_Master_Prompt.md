# Codex Master Prompt — `nhtsa_metadata` 구현 요청문

아래 내용을 Codex에 그대로 제공한다.

---

You are implementing a new project named `nhtsa_metadata` at `D:\vscode\nhtsa_metadata`.

## Project goal

Build a metadata-only catalog database for the NHTSA Vehicle Crash Test Database. This is not a download GUI. It must preserve raw NHTSA source responses, normalize important engineering filter domains into canonical tables, maintain lineage from canonical rows back to source payload/json path, and expose query/filter APIs.

Top-level principle:

> `metadata/{testNo}` is only one source. A complete database must collect the full per-test endpoint matrix raw-first, then rebuild canonical/detail/read models from those raw payloads.

## Hard boundaries

Do not implement:

- UI
- download execution
- queue/progress APIs
- waveform parsing
- TDMS/UDS/ABF/ISO parsing
- full production crawler
- automatic live API calls in default tests or verify scripts

Do implement:

- Python package `nhtsa_metadata`
- FastAPI app skeleton and query API
- SQLite + SQLAlchemy + Alembic schema
- raw/provenance tables
- canonical domain tables
- filter/read-model tables
- fixture/mock source client
- parser/normalizer
- catalog builder CLI
- field coverage reporting
- manual live validation command with explicit opt-in

## Live API safety

Default tests, `scripts/verify.ps1`, and `.harness/run.ps1` must not call external NHTSA APIs.

External live calls are allowed only when both are true:

```text
--source live
--allow-live
```

Optionally also require `NHTSA_METADATA_ALLOW_LIVE=1` or settings `allow_live=true`. If implemented, tests must verify live access is blocked by default.

## Endpoint matrix

Implement endpoint definitions for:

```text
Discovery:
- vehicle-database-test-results
- vehicle-database-test-results/by-search
- vehicle-database-test-results/by-search-vehicle optional
- vehicle-database-test-results/by-search-barrier optional
- vehicle-database-test-results/vehicleModels optional
- vehicle-database-test-results/occupant-types optional

Core:
- vehicle-database-test-results/test-no/{testNo}
- vehicle-database-test-results/metadata/{testNo}
- vehicle-database-test-results/get-test-detail/{testNo} optional

Detail:
- get-vehicle-info/{testNo}
- get-vehicle-detail-info/{vehicleNo}/{testNo}
- get-barrier-info/{testNo}
- get-occupant-info/{testNo}
- get-occupant-info/{vehNo}/{testNo}
- get-occupant-detail-information/{vehNo}/{testNo}/{occLoc}
- get-restraint-info/{vehicleNo}/{testNo}/{occupantLocation}
- get-intrusion-info/{vehicleNo}/{testNo}
- get-instrumentation-info/{testNo}?pageNumber=N
- get-instrumentation-detail-info/{curveNo}/{testNo}

Assets:
- get-multimedia-files/{testNo}
- vehicle-documents/test-no/{testNo}
```

Do not trust summary response links as the only endpoint authority. Use endpoint templates plus discovered keys.

## Implementation sequence

Implement phase by phase. Do not jump to later phases before the current phase passes verification.

Use these instruction files in order:

```text
02_Phase_0_Scaffold.md
03_Phase_1_Source_Contract.md
04_Phase_2_DB_Foundation.md
05_Phase_3_Fixtures.md
06_Phase_4_Parser_Normalizer.md
07_Phase_5_Ingestion_Rebuild.md
08_Phase_6_Query_Filter_API.md
09_Phase_7_Manual_Live_Validation.md
10_Phase_8_Scale_Readiness.md
12_Global_Acceptance_Checklist.md
```

## Required default verification

After each phase, run:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check src tests
.venv\Scripts\python.exe -m mypy src\nhtsa_metadata
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
powershell -ExecutionPolicy Bypass -File .harness\run.ps1
```

If a command fails, fix the implementation. Do not claim the phase is complete until the commands pass.

## Required phase report

At the end of each phase, write `docs/phase_reports/phase_N_*.md` with:

```markdown
# Phase N Report

## Completed
- ...

## Verification
- pytest: pass/fail
- ruff: pass/fail
- mypy: pass/fail
- harness: pass/fail

## Deviations
- ...

## Risks / TODO
- ...
```

## Important domain rules

- Store raw payloads endpoint-by-endpoint.
- Store pagination provenance.
- Store source payload observations separately from immutable payloads.
- Store source sections and field coverage.
- Store canonical lineage: source_payload_id, endpoint, section, row path, row hash, raw row JSON, extra_json.
- Normalize barrier, restraint, instrumentation, injury metrics, deformation, intrusion, media assets into first-class tables.
- Use `test_participants` to model subject vehicle, impactor vehicle, barrier, sled, other.
- Preserve zero vs null vs missing.
- Date and numeric parsing must keep raw values.
- Empty endpoints are not failures when allowed by endpoint definition.
- Read models are rebuildable derivatives, not source of truth.

## Stop conditions

Stop and report if:

- A requirement conflicts with an existing test or document.
- A live call would be needed for default verification.
- A schema decision would discard raw fields.
- A download or waveform parsing feature is accidentally introduced.

Do not perform broad redesign unless necessary. Prefer completing the phase with tests and documenting limitations.

---
