# Phase 6 — Query / Filter API 작업지시서

## 목표

DB 조회와 상태 확인 중심의 FastAPI API를 구현한다. API는 수집 실행이나 live 호출을 자동 수행하지 않는다. v1 API는 metadata catalog 조회, facet/filter, field coverage, collection run 조회를 제공한다.

## API scope

구현:

```text
GET /api/health
GET /api/tests
GET /api/tests/{test_no}
GET /api/filter-options
GET /api/coverage/fields
GET /api/collection-runs
```

선택:

```text
GET /api/source-payloads?test_no=10001
```

구현하지 않음:

```text
다운로드 실행 API
queue/job/progress API
waveform/TDMS/UDS 분석 API
live collect trigger API
UI
```

## 생성/수정 파일

```text
src/nhtsa_metadata/api/app.py
src/nhtsa_metadata/api/dependencies.py
src/nhtsa_metadata/api/schemas.py
src/nhtsa_metadata/api/routes_health.py
src/nhtsa_metadata/api/routes_tests.py
src/nhtsa_metadata/api/routes_filters.py
src/nhtsa_metadata/api/routes_coverage.py
src/nhtsa_metadata/api/routes_collection_runs.py
src/nhtsa_metadata/services/query_service.py
src/nhtsa_metadata/services/filter_service.py
src/nhtsa_metadata/services/health_service.py

tests/test_api_health.py
tests/test_api_tests.py
tests/test_api_filters.py
tests/test_api_coverage.py
tests/test_api_collection_runs.py

docs/phase_reports/phase_6_query_filter_api.md
```

## Dependency policy

- FastAPI dependency로 DB session 주입.
- Test에서는 tmp SQLite DB + fixture ingestion 사용.
- API endpoint는 live NHTSA API 호출 금지.
- Raw payload 전문은 default response에서 제외.

## Response schemas

### Health

```python
class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str
    database_url_configured: bool
    database_connectivity: str
    migration_status: str | None = None
    database_path: str | None = None
```

### Test list item

```python
class TestListItem(BaseModel):
    test_no: int
    test_reference_no: str | None
    test_type: str | None
    test_configuration: str | None
    test_date: date | None
    test_date_raw: str | None
    contractor_study_title: str | None
    closing_speed: Decimal | None
    impact_angle: Decimal | None
    vehicle_makes: list[str]
    vehicle_models: list[str]
    model_year_min: int | None
    model_year_max: int | None
    participant_kinds: list[str]
    asset_kinds: list[str]
```

### Test detail

```python
class TestDetailResponse(BaseModel):
    test: TestCore
    participants: list[ParticipantOut]
    vehicles: list[VehicleOut]
    barriers: list[BarrierOut]
    occupants: list[OccupantOut]
    restraints: list[RestraintOut]
    instrumentation_channels: list[InstrumentationChannelOut]
    injury_metrics: list[InjuryMetricOut]
    deformation_measurements: list[DeformationMeasurementOut]
    intrusion_measurements: list[IntrusionMeasurementOut]
    media_assets: list[MediaAssetOut]
    source_payload_summary: list[SourcePayloadSummaryOut]
```

Default:

```text
include_raw=false
```

`include_raw=true`는 v1에서 400으로 reject하거나 별도 raw endpoint를 구현한다.

## `GET /api/health`

반환:

- DB connect ok/error.
- migration status 가능하면 포함.
- sanitized DB path/URL.
- secret 출력 금지.

## `GET /api/tests`

Query parameters:

```text
q
limit
offset
sort_by
sort_dir

test_type
test_configuration
vehicle_make
vehicle_model
model_year_from
model_year_to
closing_speed_from
closing_speed_to
impact_angle_from
impact_angle_to
participant_kind
barrier_rigidity
barrier_shape
occupant_location
dummy_type
restraint_type
restraint_deployment
sensor_type
sensor_location
sensor_attachment
sensor_axis
sensor_unit
injury_metric_code
injury_metric_min
injury_metric_max
deformation_code
asset_kind
has_uds_or_tdms_package
```

Filter strategy:

- scalar filters: `tests`, `test_filter_summary`.
- facet filters: `test_facets` existence subqueries.
- numeric metric range: canonical table.
- cross-filter: AND.
- multiple values in same facet: OR.

Example:

```text
/api/tests?vehicle_make=CADILLAC&restraint_type=FRONTAL%20AIRBAG&sensor_type=ACCELEROMETER
```

## `GET /api/tests/{test_no}`

- missing -> 404.
- canonical detail rows 포함.
- media asset registry 포함, 다운로드 없음.
- instrumentation rows는 많을 수 있으므로 pagination/limit 제공.

권장 parameters:

```text
include_instrumentation=true
instrumentation_limit=500
instrumentation_offset=0
```

## `GET /api/filter-options`

Parameters:

```text
facet_name optional
limit default 1000
```

Return example:

```json
{
  "facets": {
    "vehicle_make": [{"value": "CADILLAC", "count": 1}],
    "sensor_type": [{"value": "ACCELEROMETER", "count": 1}]
  }
}
```

Hardcode 금지. DB contents 기반.

## `GET /api/coverage/fields`

Parameters:

```text
endpoint_name
section_name
mapping_status
limit
offset
```

`source_field_catalog` rows 반환.

## `GET /api/collection-runs`

Parameters:

```text
limit
offset
status
run_type
mode
```

collection run summary와 item counts 반환.

## Services

`query_service.py`:

```python
class QueryService:
    def list_tests(self, filters: TestFilters, limit: int, offset: int) -> Paginated[TestListItem]: ...
    def get_test_detail(self, test_no: int, include_raw: bool = False, instrumentation_limit: int = 500, instrumentation_offset: int = 0) -> TestDetail | None: ...
```

`filter_service.py`:

```python
class FilterService:
    def get_filter_options(self, facet_name: str | None = None, limit: int = 1000) -> dict[str, list[FacetOption]]: ...
```

## API tests

Fixture DB는 ingestion service로 준비한다.

### Health

- `/api/health` returns ok.
- DB connectivity included.

### Tests list/detail

- `/api/tests` returns 10001/10003.
- `/api/tests/10001` returns vehicles/barriers/occupants/media.
- missing test_no -> 404.
- raw payload not included by default.

### Filters

필수 filter cases:

```text
vehicle_make=CADILLAC -> includes 10001
vehicle_make=CHEVROLET -> includes 10003
participant_kind=impactor_vehicle -> includes 10003
barrier_rigidity=RIGID -> includes 10001 if fixture has barrier
restraint_type=FRONTAL AIRBAG -> includes 10001
sensor_type=<fixture sensor> -> includes 10001
injury_metric_code=HIC -> includes relevant tests
deformation_code=DPD1 -> includes relevant tests
asset_kind=photo -> includes media tests
has_uds_or_tdms_package=true -> includes 10001 if fixture documents include UDS/TDMS
compound filter vehicle_make + asset_kind
```

### Coverage

- `/api/coverage/fields` returns mapped/unmapped rows.
- mapping_status filter works.

### Collection runs

- `/api/collection-runs` returns fixture collect run.

## 완료 기준

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check src tests
.venv\Scripts\python.exe -m mypy src\nhtsa_metadata
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
powershell -ExecutionPolicy Bypass -File .harness\run.ps1
```

추가 조건:

```text
required API endpoints exist
API tests use fixture DB only
filter options are DB-driven
compound facet filter works
raw payload excluded by default
no live API call from API code paths
```
