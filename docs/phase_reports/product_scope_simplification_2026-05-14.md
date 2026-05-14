# Product Scope Simplification Report - 2026-05-14

## Summary

Requested order was `2 -> 1 -> 3 -> 4 -> 5 -> 6`.

The repository is currently green and clean after removing untracked experiment/report artifacts from the worktree. The remaining strategic issue is scope: the existing repository was intentionally built as a metadata-only DB project, while the new product goal is narrower and more practical:

1. GUI에서 다운로드
2. DB 구축
3. DB 관리

This is a scope change because the current README/AGENTS guardrails explicitly mark UI and download execution as out of scope. The recommendation is to make a deliberate product-scope reset instead of continuing to pile pilot, classification, schema-optimization, and agent-reporting artifacts into the same main surface.

## Assumptions

- Keep the existing 2011+ `test_date >= 2011-01-01` scope rule.
- Keep raw/provenance payload preservation and rebuildable canonical/read-model layers.
- Do not run live NHTSA API calls from default tests, verify scripts, or harness.
- Do not commit `data/` DB/CSV/runtime artifacts.
- Treat `D:\vscode\pulse_analysis\data\db\nhtsa_data.db` as a bounded manifest seed only.
- The new GUI download feature means controlled file download from known `media_assets.source_url` records, not waveform/TDMS/UDS/ABF/ISO/ZIP parsing.

## Completed Sequence

### 2. Untracked artifact cleanup

Moved generated/untracked planning bundles and report artifacts out of the repository worktree:

- `nhtsa_codex_hermes_plan.zip`
- `nhtsa_codex_hermes_plan/`
- `nhtsa_codex_hermes_review_bundle_2026-05-13.zip`
- `nhtsa_codex_hermes_review_bundle_2026-05-13/`
- `nhtsa_metadata_refactoring_md_bundle_2026-05-07.zip`
- `docs/codex_reports/`
- `docs/phase_reports/codex_hermes_lite_integration_review_2026-05-13.md`

Archive root:

```text
D:\vscode\nhtsa_metadata_cleanup_archive\20260514_141229
```

### 1. Verification

Full default checks passed before this report was written:

```text
ruff check src tests                    PASS
mypy src/nhtsa_metadata                 PASS, 55 source files
pytest -q                               PASS, 136 passed, 4 warnings
scripts/verify.ps1                      PASS, 136 passed, 4 warnings
.harness/run.ps1                        PASS, 136 passed, 4 warnings
```

Warnings are the known non-blocking pytest collection warnings around SQLAlchemy model class `TestFilterSummary`.

### 3. Dependency map and core boundary

High-level dependency direction:

```text
CLI/API
  -> config
  -> db/session/models
  -> sources/nhtsa_crash clients/parsers/contracts
  -> services
       -> raw/provenance persistence
       -> canonical mapping/upsert
       -> read-model/materialized filter DB
       -> validation/reporting/research services
```

Central modules by practical dependency importance:

- `nhtsa_metadata.db.models`
- `nhtsa_metadata.config`
- `nhtsa_metadata.db.session`
- `nhtsa_metadata.sources.nhtsa_crash.contracts`
- `nhtsa_metadata.sources.nhtsa_crash.endpoints`
- `nhtsa_metadata.sources.nhtsa_crash.live_client`
- `nhtsa_metadata.sources.nhtsa_crash.parsers`
- `nhtsa_metadata.sources.nhtsa_crash.normalization`
- `nhtsa_metadata.services.catalog_builder`
- `nhtsa_metadata.services.ingestion_service`
- `nhtsa_metadata.services.source_payload_service`
- `nhtsa_metadata.services.canonical_mapper`
- `nhtsa_metadata.services.canonical_upsert`
- `nhtsa_metadata.services.read_model_builder`
- `nhtsa_metadata.services.filter_db_materializer`
- `nhtsa_metadata.api.app`
- `nhtsa_metadata.cli`

Recommended product-core set for the new goal:

```text
src/nhtsa_metadata/
  config.py
  constants.py
  cli.py                         slimmed or split
  api/app.py                     GUI-facing query/read/download-control API
  db/
    base.py
    migrations.py
    models.py
    session.py
  sources/nhtsa_crash/
    client.py
    contracts.py
    dtos.py
    endpoints.py
    field_aliases.py
    field_catalog.py
    fixtures.py
    fixture_factory.py
    live_client.py
    normalization.py
    parsers.py
  services/
    catalog_builder.py           bounded DB build/collect
    collection_runs.py           DB build run tracking
    source_payload_service.py    raw/provenance persistence
    ingestion_service.py         raw -> canonical/read-model orchestration
    canonical_mapper.py
    canonical_upsert.py
    read_model_builder.py
    filter_db_materializer.py    GUI/filter-ready DB output
    filter_db_reports.py
    vehicle_filter_fields.py
    scope.py
    db_health.py
```

Keep as `ops/validation` for now, not product UI surface:

```text
services/schema_audit.py
services/endpoint_completeness.py
services/coverage_service.py
services/scale_readiness.py
services/code_values.py
scripts/verify.ps1
scripts/live_pilot_validate.ps1
.harness/run.ps1
```

Review/archive candidates after product scope is frozen:

```text
services/discovery_authority.py
services/full_cover_readiness.py
services/rule_classifier.py
services/classification_accounting.py
services/classification_lineage.py
services/schema_optimization.py
services/schema_v1_policy.py
services/live_baseline_assertions.py
instructions/
nhtsa_metadata_codex_work_orders/
most historical docs/phase_reports/*
```

Important caveat: do not delete these immediately. Some still have tests, validation evidence, or indirect dependencies. First move their CLI surface behind a `legacy` or `research` group, then remove only after green tests and owner approval.

### 4. GUI download / DB build / DB management simplification candidates

#### Target product surface

Recommended top-level product commands/API capabilities:

```text
DB build
- build manifest from bounded live source or existing manifest
- collect metadata for approved manifest
- rebuild canonical/read-model from stored raw payloads
- materialize GUI/filter-ready DB

DB management
- health/status
- list DBs / current DB metadata
- backup DB
- vacuum/analyze DB
- migrate/upgrade
- validate DB using schema audit and scope audit
- open read/query API for GUI

GUI download
- list downloadable media/document/data-package assets from `media_assets`
- enqueue selected asset downloads
- show queue/progress/history
- store downloaded files outside git-tracked source tree
- never parse waveform/package contents by default
```

#### Existing support

Already present:

- `media_assets` stores URL metadata and suggested filenames.
- API exposes test details and `media_assets` metadata.
- `catalog collect` and `catalog rebuild` support DB construction path.
- `schema materialize-filter-db` creates GUI/filter-ready DB from source DB.
- `scripts/live_pilot_validate.ps1` bundles collect, coverage, schema audit, scale report, and API smoke.

Missing for the new product goal:

- No GUI implementation in this repository.
- No actual download queue/service.
- No DB backup/vacuum/compact/list command surface.
- No product-level CLI grouping; current CLI is crowded with research/phase commands.
- README/AGENTS still state UI and download execution are out of scope.

#### Recommended reduction plan

Phase A - declare scope reset:

1. Update README and AGENTS to say new product target is GUI download + DB build + DB management.
2. Preserve safety rules: no default live calls, no full crawler, no waveform/package parsing.
3. Define download as controlled asset download only, sourced from DB `media_assets` rows.

Phase B - split command surface:

1. Keep public product commands small:
   - `nhtsa-metadata db health`
   - `nhtsa-metadata db build`
   - `nhtsa-metadata db rebuild`
   - `nhtsa-metadata db materialize-filter`
   - `nhtsa-metadata db backup`
   - `nhtsa-metadata db vacuum`
   - `nhtsa-metadata download list-assets`
   - `nhtsa-metadata download enqueue`
   - `nhtsa-metadata api serve`
2. Move current phase/research commands under `legacy`, `ops`, or `research` before deletion.
3. Add tests that prove old core DB build behavior still works.

Phase C - archive historical material:

1. Move old work orders and phase reports to `docs/archive/` or outside the repo.
2. Keep only current architecture, operations, schema, validation, and product-scope docs in the main docs index.
3. Keep runtime DBs under ignored `data/` or move large historical DBs to external storage.

Phase D - add GUI download safely:

1. Add a `downloads` table for jobs/history.
2. Add a downloader service that accepts only DB-registered asset IDs.
3. Store files in a configured external download directory, not under tracked source.
4. Add progress/status APIs for GUI.
5. Add tests using mocked HTTP; no live network in default verification.

### 5. Hermes/Codex automation scripts

Two untracked dev-automation files were inspected:

```text
scripts/codex_nightly_report.ps1
scripts/session_search.py
```

Checks:

```text
codex_nightly_report.ps1 parse check        PASS
session_search.py py_compile                PASS
session_search.py smoke search              PASS
```

Decision:

They are dev/agent workflow helpers, not product-core for GUI download / DB build / DB management. They were archived out of the repo worktree.

Archive root:

```text
D:\vscode\nhtsa_metadata_cleanup_archive\20260514_142001\dev_automation_scripts
```

After archiving, `git status --short --untracked-files=all` was clean.

### 6. Live pilot / 100-test expansion readiness

Live API was not executed.

Safety negative checks were executed and passed:

```text
catalog build-manifest --source live without --allow-live
  -> failed as expected
  -> output manifest not created

catalog build-manifest --source live --allow-live with NHTSA_METADATA_ALLOW_LIVE unset/empty
  -> failed as expected
  -> output manifest not created
```

Result:

```text
LIVE_NEGATIVE_CHECKS_PASS
```

Current ignored `data/` artifacts include:

```text
CSV:
- data/full_2011plus_authoritative_manifest_refresh_2026-05-03.csv       3900 rows
- data/incremental_refresh_2026-05-03_missing_9_manifest.csv             9 rows
- data/live_completeness_audit_2026-05-03_year_slice_manifest.csv        3724 rows

SQLite:
- data/full_2011plus_metadata_filter_ready_2026-05-04.sqlite             ~2.76 GB
- data/full_2011plus_metadata_only_refresh_2026-05-03.sqlite             ~2.65 GB
- data/refactor_validation_filter_ready_2026-05-07.sqlite                ~2.76 GB
- data/nhtsa_metadata.sqlite                                             ~0.5 MB
```

Readiness conclusion:

- Default verification is green.
- Live safety guardrails are working.
- The repo has prior 100-test planning docs and 1000-test live reports.
- The previously documented `data/stratified_live_pilot_2011plus_100_manifest_candidate.csv` is not currently present in `data/`.
- A 100-test live manifest build or collect should not be run until the owner explicitly approves the live step and target output paths.

## Current Git State

After implementation, the worktree contains tracked source/doc/test changes plus this phase report.
Ignored `data/` artifacts remain ignored and should not be staged.

## Implementation Pass - Product Scope Reset, DB Management, GUI Downloads

The recommended next implementation plan was executed with test-first coverage for new behavior.

### Scope reset docs

Updated:

- `README.md`
- `AGENTS.md`
- `docs/operations.md`

The docs now define the active product surface as:

1. GUI-facing controlled downloads from DB `media_assets`
2. DB build/rebuild/materialization support
3. Local DB management

Historical schema research, large pilot artifacts, and classification experiments remain available as
ops/validation references but are no longer the main product surface.

### DB management commands

Added service:

- `src/nhtsa_metadata/services/db_management.py`

Added CLI:

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli db status
.venv\Scripts\python.exe -m nhtsa_metadata.cli db backup --output data\backup.sqlite
.venv\Scripts\python.exe -m nhtsa_metadata.cli db vacuum
```

Implemented behavior:

- SQLite DB status/inspect report with table counts and file size
- SQLite backup using `sqlite3.Connection.backup`
- SQLite `VACUUM` with optional `ANALYZE`

### GUI download backend

Added configuration:

- `NHTSA_METADATA_DOWNLOAD_DIR`, default `data/downloads`

Added DB model and migration:

- `DownloadJob` table, created by `ensure_schema`/SQLAlchemy metadata for local SQLite DBs
- Alembic migration `alembic/versions/0007_download_jobs.py`

Added service:

- `src/nhtsa_metadata/services/downloads.py`

Added API endpoints:

```text
GET  /api/download-assets
POST /api/download-jobs
GET  /api/download-jobs
POST /api/download-jobs/{job_id}/run
```

Added CLI:

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli download list-assets
.venv\Scripts\python.exe -m nhtsa_metadata.cli download enqueue --media-asset-id 1
.venv\Scripts\python.exe -m nhtsa_metadata.cli download list-jobs
.venv\Scripts\python.exe -m nhtsa_metadata.cli download run-job --job-id 1
```

Safety boundary:

- Download jobs can only be created from existing DB `media_assets` rows.
- Default verification injects mocked fetchers and performs no real downloads.
- The actual runner only accepts HTTP(S) source URLs.
- Download files are runtime artifacts under the configured download directory.
- No waveform/package parsing was added.

### New tests

Added:

- `tests/test_db_management.py`
- `tests/test_downloads.py`
- `tests/test_api_downloads.py`

TDD red check was observed before implementation:

```text
ModuleNotFoundError: No module named 'nhtsa_metadata.services.db_management'
ModuleNotFoundError: No module named 'nhtsa_metadata.services.downloads'
```

Final verification after implementation:

```text
ruff check src tests alembic            PASS
mypy src/nhtsa_metadata                 PASS, 57 source files
pytest -q                               PASS, 152 passed, 4 warnings
scripts/verify.ps1                      PASS, 152 passed, 4 warnings
.harness/run.ps1                        PASS, 152 passed, 4 warnings
```

Warnings remain the known non-blocking pytest collection warnings around SQLAlchemy model class
`TestFilterSummary`.

### DB baseline and data archive pass

Keeper selected:

```text
data/full_2011plus_metadata_filter_ready_2026-05-04.sqlite
```

Selection evidence:

- 3,900 `tests` rows and 3,900 `test_filter_summary` rows
- 290,845 `media_assets` rows for GUI-controlled downloads
- `test_date` range: 2011-01-03 through 2025-11-19
- Product-named `filter_ready` artifact rather than validation-only artifact
- Contains the newer filter/classification tables absent from the older metadata-only refresh DB

The keeper was updated locally with an empty `download_jobs` table and indexes so the GUI download backend can enqueue jobs against the current baseline DB.

Archived non-keeper runtime artifacts:

```text
D:\vscode\nhtsa_metadata_data_archive\20260514_150612
```

Moved 25 files, including non-keeper SQLite DBs, prior manifest CSVs, and Stage K JSON/MD/stdout runtime reports. The archive includes a `MANIFEST.json` with original paths, archive paths, sizes, and SHA256 checksums. Tracked `data/.gitkeep` was restored, and checked-in `data/schema/` reference files were not moved.

Added `docs/db_baseline.md` to record the keeper and archive policy.

### CLI product/ops/legacy split

The top-level CLI help now focuses on product-facing groups:

```text
catalog
db
download
ops
legacy
```

Backward-compatible top-level aliases remain executable but hidden from top-level help:

```text
coverage
scale
schema
```

Operational validation/reporting commands are available under `ops`, and historical schema/research commands are available under `legacy`.

Added product alias:

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog materialize-filter-db --help
```

New test coverage:

- `tests/test_cli_product_surface.py`

TDD red check was observed before implementation: `ops`/`legacy` groups and `catalog materialize-filter-db` were missing, then passed after the CLI split.

### GUI frontend connection

Added local FastAPI-served asset console:

```text
GET /                  -> static GUI shell
GET /static/gui.css    -> console styling
GET /static/gui.js     -> browser behavior/API wiring
```

Added files:

- `src/nhtsa_metadata/api/static/index.html`
- `src/nhtsa_metadata/api/static/gui.css`
- `src/nhtsa_metadata/api/static/gui.js`
- `tests/test_gui_frontend.py`

Frontend behavior:

- Loads `/api/health` to show API/environment status.
- Loads `/api/download-assets` with `limit`, `offset`, `test_no`, `asset_kind`, and `q` filters.
- Shows filtered totals and page counts for the large keeper DB asset registry.
- Queues selected assets through `POST /api/download-jobs`.
- Lists jobs through `GET /api/download-jobs` with status filter chips.
- Requires a browser confirmation before calling `POST /api/download-jobs/{job_id}/run`, because that endpoint may perform a real HTTP(S) download.

Design basis:

- Linear-inspired dark native surface, compressed heading scale, subtle translucent borders.
- Supabase-inspired emerald accent and developer-console posture.
- Vercel-inspired precise table/card spacing and restrained interaction states.

MCP note:

- The native MCP skill was loaded and the Hermes config was checked for `mcp_servers`; none are configured/exposed in this session, so implementation used the available repo, browser, and test tools plus the loaded design skills.

Targeted verification:

```text
pytest tests/test_gui_frontend.py -q                                      PASS, 2 passed
ruff/mypy targeted GUI/backend checks                                    PASS
pytest tests/test_api_downloads.py tests/test_downloads.py tests/test_gui_frontend.py -q  PASS, 8 passed
browser visual check at http://127.0.0.1:8020/                           PASS
browser console after load/filter                                        PASS, no JS errors
```

Browser smoke confirmed the real keeper DB page loads `50 / 290845` assets, search filtering reduced `v07201R002` to `1 / 1`, and the visual layout had no commit-blocking overlap/clipping issues.

## Remaining Next Steps

1. If a downstream GUI exists, either embed this local console route or port its API wiring to that frontend.
2. If a newer DB becomes the official baseline later, repeat the `docs/db_baseline.md` keeper/archive process.
3. Consider a later internal code-module move for legacy/research services only after the CLI split remains stable and green.

## Stop Rules

Do not proceed to code deletion, live collection, or broad legacy module removal until these are explicit:

- Whether the GUI lives in this repo or a downstream repo.
- Whether live 100-test manifest build is approved.
- Whether internal legacy/research modules should be physically moved or deleted after the CLI split.
- Which replacement DB becomes keeper if the current baseline is superseded.
