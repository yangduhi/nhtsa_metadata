# Phase 8 — Scale Readiness 작업지시서

## 목표

SQLite 기준으로 수십~수백 건 manifest 수집을 검증하고, index/read-model/coverage report가 확장 가능한지 확인한다. PostgreSQL 이전 조건과 schema portability를 문서화한다.

## 범위

구현/점검:

```text
bounded manifest collection
resume behavior practical test
batch commit policy
index review
DB size/reporting
field coverage growth report
read model rebuild timing
PostgreSQL migration readiness document
```

제외:

```text
full 10k+ crawl 자동화
production scheduler
UI
파일 다운로드
waveform/data package parsing
```

## 생성/수정 파일

```text
src/nhtsa_metadata/services/scale_report_service.py
src/nhtsa_metadata/cli.py
scripts/scale_check_fixture.ps1

docs/scale_readiness.md
docs/2026-04-28__migration-notes__current__postgresql-migration-notes.md
docs/phase_reports/2026-04-28__bootstrap-phase-8__pass__phase-8-report.md

tests/test_scale_report_fixture.py
tests/test_resume_behavior.py
tests/test_read_model_rebuild_scale_fixture.py
```

## CLI additions

Scale report:

```powershell
python -m nhtsa_metadata.cli scale report --database-url sqlite:///data/live_validation.sqlite
```

출력:

```text
DB path
DB size bytes
row counts by table
source_payload count by endpoint
top unmapped fields
field coverage mapped/unmapped ratio
read model rows
facet count by facet_name
latest collection run summary
```

Read model rebuild all:

```powershell
python -m nhtsa_metadata.cli catalog rebuild-read-models --database-url sqlite:///data/live_validation.sqlite
```

Optional SQLite helper:

```powershell
python -m nhtsa_metadata.cli db analyze --database-url sqlite:///data/live_validation.sqlite
```

## Batch/transaction policy

문서화 및 가능하면 구현:

```text
Per test_no transaction for canonical ingestion
source_payload save commit policy 명시
collection_run item status update even when test fails
failed test_no should not roll back prior succeeded test_no items
```

권장:

```text
1. collection_run 생성 transaction
2. per test_no transaction for endpoints + canonical rows
3. 실패 시 current test_no rollback
4. failed item 별도 short transaction으로 기록
```

더 단순한 구현을 쓰면 limitation을 phase report에 기록한다.

## Index review

확인할 index 또는 equivalent:

```text
tests.test_no unique
tests.test_type
tests.test_configuration
tests.test_date
vehicles(test_id, source_vehicle_no) unique
vehicles(make, model, model_year)
source_payloads(test_no, endpoint_name)
source_payloads(payload_hash)
source_payloads(fetched_at)
instrumentation_channels(test_id, curve_no) unique
instrumentation_channels(sensor_type)
instrumentation_channels(sensor_location)
instrumentation_channels(sensor_axis)
test_facets(facet_name, facet_value)
test_facets(test_id, facet_name)
media_assets(test_id, asset_kind, canonical_url_hash) unique
```

금지/지양:

```text
large full JSON payload index
full-text index on source_payloads.payload_json
indexing every raw field before query needs are known
```

## PostgreSQL migration notes

`docs/2026-04-28__migration-notes__current__postgresql-migration-notes.md` 포함 내용:

```text
SQLAlchemy JSON -> PostgreSQL JSONB consideration
SQLite NUMERIC/DateTime behavior vs PostgreSQL strictness
Alembic migration compatibility
index differences
connection URL format
batch insert optimization
payload JSON storage size expectations
backup/restore strategy
```

## Scale fixture tests

Default tests는 live API에 의존하지 않는다. synthetic scale fixtures 또는 generator를 사용한다.

Requirements:

```text
Generate 50 synthetic test payload sets from base fixtures
Each test has unique test_no
Vary vehicle_make/model/year, facets, asset kinds
Ingest all via fixture client
Rebuild read models
Run scale report
```

50이 너무 느리면 default tests는 20으로 낮추고 manual 100-test check를 문서화한다.

## Resume behavior tests

Simulate:

```text
manifest has 5 test_no
2 succeed
1 fails
process interrupted
resume skips succeeded and retries failed/pending
```

Assertions:

```text
succeeded rows not duplicated
failed item gets retried
collection_run/run_item status clear
```

## Manual scale script

`scripts/scale_check_fixture.ps1`:

- temp SQLite DB 생성.
- synthetic fixture manifest 생성.
- fixture collect 실행.
- read model rebuild.
- scale report.
- live API 호출 없음.

## `docs/scale_readiness.md`

필수 내용:

```markdown
# Scale Readiness

## Current Scope
- metadata-only
- SQLite baseline
- fixture/manual live validation

## Tested Scale
| mode | test count | source payloads | canonical rows | DB size | read model rebuild time |
|---|---:|---:|---:|---:|---:|

## Index Strategy
- ...

## Known Bottlenecks
- ...

## PostgreSQL Migration Trigger
- DB size exceeds ...
- collect/read query latency exceeds ...
- concurrent access needed
- JSON query requirements increase

## Not Implemented
- full crawler scheduler
- file downloads
- waveform parsing
```

## 완료 기준

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check src tests
.venv\Scripts\python.exe -m mypy src\nhtsa_metadata
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
powershell -ExecutionPolicy Bypass -File .harness\run.ps1
```

Additional:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\scale_check_fixture.ps1
```

추가 조건:

```text
synthetic scale fixture collection succeeds
scale report prints table counts and field coverage
resume behavior test passes
PostgreSQL migration notes exist
large JSON payload index is not added
```
