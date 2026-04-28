# Global Acceptance Checklist — `nhtsa_metadata`

## Repository / Bootstrap

- [ ] Project root is `D:\vscode\nhtsa_metadata`.
- [ ] Package import path is `nhtsa_metadata`.
- [ ] Fresh `.venv`; no copied `.venv`.
- [ ] Fresh Git repository; no copied `.git`.
- [ ] Runtime data, DB, caches, screenshots, response dumps are not copied.
- [ ] `pyproject.toml` contains runtime and dev dependencies.
- [ ] `scripts/verify.ps1` exists.
- [ ] `.harness/run.ps1` exists.

## Documentation

- [ ] `README.md` defines metadata-only scope.
- [ ] `AGENTS.md` contains guardrails.
- [ ] `docs/source_contract.md` exists.
- [ ] `docs/source_endpoint_matrix.md` includes `get-test-detail/{testNo}` optional endpoint.
- [ ] `docs/source_field_aliases.md` exists.
- [ ] `docs/source_anomalies.md` documents wrong summary link, pagination, empty endpoint, multi-vehicle, date anomalies, zero/null.
- [ ] `docs/db_schema_contract.md` exists.
- [ ] `docs/db_schema.md` matches implemented schema.
- [ ] `docs/catalog_builder_contract.md` exists.
- [ ] `docs/filtering_contract.md` exists.
- [ ] `docs/field_coverage_contract.md` exists.
- [ ] `docs/operations.md` exists.
- [ ] `docs/phase_reports/` contains phase reports.

## Source Contract

- [ ] Endpoint definitions exist in code.
- [ ] Discovery/core/detail/assets groups exist.
- [ ] Instrumentation endpoint is paginated.
- [ ] Empty endpoints are allowed where appropriate.
- [ ] Summary links are not used as sole authority.
- [ ] Occupant location path values are URL-encoded.

## DB Schema

Raw/provenance:

- [ ] `collection_runs`
- [ ] `collection_run_items`
- [ ] `source_endpoints`
- [ ] `source_payloads`
- [ ] `source_payload_observations`
- [ ] `source_payload_sections`
- [ ] `source_field_catalog`
- [ ] `source_conflicts`
- [ ] `canonical_row_sources`

Canonical:

- [ ] `tests`
- [ ] `test_participants`
- [ ] `vehicles`
- [ ] `barriers`
- [ ] `occupants`
- [ ] `restraints`
- [ ] `instrumentation_channels`
- [ ] `instrumentation_channel_details`
- [ ] `injury_metrics`
- [ ] `deformation_measurements`
- [ ] `intrusion_measurements`
- [ ] `media_assets`
- [ ] `code_values`

Read model:

- [ ] `test_filter_summary`
- [ ] `test_facets`
- [ ] `asset_summary`
- [ ] `field_coverage_snapshots`

DB properties:

- [ ] Alembic upgrade head succeeds.
- [ ] Alembic downgrade base succeeds.
- [ ] FK uses internal ids.
- [ ] Natural unique constraints exist.
- [ ] Canonical rows have lineage fields.
- [ ] JSON columns store dict/list values.

## Fixtures

- [ ] `metadata_10.json` exists.
- [ ] `metadata_30.json` exists.
- [ ] `metadata_10001.json` exists.
- [ ] `metadata_10003.json` exists.
- [ ] 10001 summary fixture reproduces wrong `barrierInformation` link.
- [ ] 10003 vehicle fixture has at least two vehicles.
- [ ] 10003 impactor-as-vehicle is represented.
- [ ] 10003 barrier empty fixture exists.
- [ ] 30 fixture represents zero/null/missing metrics.
- [ ] 10001 instrumentation pagination fixture exists.
- [ ] 10001 media/documents fixture includes asset/data package types.
- [ ] `live_sample_manifest.csv` exists.

## Parser / Normalizer

- [ ] Metadata export sections are recognized.
- [ ] API detail endpoint results are recognized.
- [ ] Field catalog observations are generated.
- [ ] Unknown fields are preserved.
- [ ] Date parser separates raw/parsed/status.
- [ ] Number parser separates raw/parsed/status.
- [ ] `0`, `'0'`, `null`, missing are distinguished.
- [ ] Injury metrics are long-form rows.
- [ ] Deformation measurements are long-form rows.
- [ ] Media assets are inferred without downloading.
- [ ] 10003 impactor maps to `impactor_vehicle`.

## Ingestion / Rebuild

- [ ] Source payload saved even if parser later fails.
- [ ] Source payload observation recorded per fetch.
- [ ] Source sections recorded.
- [ ] Field catalog upsert works.
- [ ] Canonical upsert is idempotent.
- [ ] `canonical_row_sources` rows are created.
- [ ] Conflict tracking works or is safely stubbed with tests.
- [ ] Read model rebuild works.
- [ ] Same fixture re-ingest does not duplicate canonical rows.
- [ ] Rebuild from source_payloads restores canonical rows.

## CLI

- [ ] `python -m nhtsa_metadata.cli version`
- [ ] `python -m nhtsa_metadata.cli health`
- [ ] `catalog discover`
- [ ] `catalog collect-test`
- [ ] `catalog collect`
- [ ] `catalog rebuild`
- [ ] `coverage report`
- [ ] `catalog assert-live-baseline`
- [ ] `scale report` if Phase 8 implemented.
- [ ] `--dry-run` writes no DB rows.
- [ ] `--source live` without `--allow-live` fails.
- [ ] default commands/tests use fixture/mock.

## API

- [ ] `GET /api/health`
- [ ] `GET /api/tests`
- [ ] `GET /api/tests/{test_no}`
- [ ] `GET /api/filter-options`
- [ ] `GET /api/coverage/fields`
- [ ] `GET /api/collection-runs`
- [ ] raw payload excluded by default.
- [ ] facet options are DB-driven.
- [ ] compound filters work.

## Filters

- [ ] test_type
- [ ] test_configuration
- [ ] vehicle_make
- [ ] vehicle_model
- [ ] model_year
- [ ] closing_speed_range
- [ ] impact_angle
- [ ] participant_kind
- [ ] barrier_rigidity
- [ ] barrier_shape
- [ ] occupant_location
- [ ] dummy_type
- [ ] restraint_type
- [ ] restraint_deployment
- [ ] sensor_type
- [ ] sensor_location
- [ ] sensor_attachment
- [ ] sensor_axis
- [ ] sensor_unit
- [ ] injury_metric_code
- [ ] injury_metric_range
- [ ] deformation_code
- [ ] asset_kind
- [ ] has_uds_or_tdms_package

## Live Validation

- [ ] Live client blocked by default.
- [ ] Manual live command requires `--source live --allow-live`.
- [ ] `scripts/live_validate.ps1 -AllowLive` exists.
- [ ] 10001 baseline assertions implemented.
- [ ] 10003 baseline assertions implemented.
- [ ] Empty intrusion/barrier endpoint not misclassified as failure.
- [ ] Live phase report truthfully states whether live validation was executed.

## Scale Readiness

- [ ] Synthetic scale fixture test exists.
- [ ] Resume behavior test exists.
- [ ] Scale report command exists.
- [ ] Index strategy documented.
- [ ] `docs/postgresql_migration_notes.md` exists.
- [ ] No large JSON payload index added.

## Final Verification Commands

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check src tests
.venv\Scripts\python.exe -m mypy src\nhtsa_metadata
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
powershell -ExecutionPolicy Bypass -File .harness\run.ps1
```

Optional manual live validation:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\live_validate.ps1 -AllowLive
```

Do not mark live validation as passed unless this command or equivalent manual live command was actually executed.
