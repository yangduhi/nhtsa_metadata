# Phase 1 — Source Contract 작업지시서

## 목표

NHTSA source contract를 구현 전에 문서와 코드 상수로 고정한다. 이 phase에서는 아직 live 수집을 구현하지 않는다.

완료 목표:

```text
endpoint matrix 확정
source anomaly 정책 확정
field alias map 초안 작성
fixture/live validation manifest 작성
source client interface skeleton 작성
기본 verify에서 문서 존재 여부와 live 호출 금지 확인
```

## 생성/수정 문서

```text
docs/2026-04-28__source-contract__current__source-contract.md
docs/2026-04-28__source-contract__current__source-endpoint-matrix.md
docs/2026-04-28__source-contract__current__source-field-aliases.md
docs/2026-04-28__source-contract__current__source-anomalies.md
docs/2026-04-28__contract__current__catalog-builder-contract.md
docs/2026-04-28__contract__current__filtering-contract.md
docs/2026-04-28__contract__current__field-coverage-contract.md
docs/2026-04-28__contract__current__db-schema-contract.md
docs/2026-04-28__operations__current__operations.md
docs/phase_reports/2026-04-28__bootstrap-phase-1__pass__phase-1-report.md
```

## Endpoint matrix

Base URL:

```text
https://nrd.api.nhtsa.dot.gov/nhtsa/vehicle/api/v1
```

Discovery:

```text
GET /vehicle-database-test-results
GET /vehicle-database-test-results/by-search
GET /vehicle-database-test-results/by-search-vehicle      # optional
GET /vehicle-database-test-results/by-search-barrier      # optional
GET /vehicle-database-test-results/vehicleModels          # optional
GET /vehicle-database-test-results/occupant-types         # optional
```

Core:

```text
GET /vehicle-database-test-results/test-no/{test_no}
GET /vehicle-database-test-results/metadata/{test_no}
GET /vehicle-database-test-results/get-test-detail/{test_no}   # optional core detail
```

Detail:

```text
GET /vehicle-database-test-results/get-vehicle-info/{test_no}
GET /vehicle-database-test-results/get-vehicle-detail-info/{vehicle_no}/{test_no}
GET /vehicle-database-test-results/get-barrier-info/{test_no}
GET /vehicle-database-test-results/get-occupant-info/{test_no}
GET /vehicle-database-test-results/get-occupant-info/{vehicle_no}/{test_no}
GET /vehicle-database-test-results/get-occupant-detail-information/{vehicle_no}/{test_no}/{occupant_location}
GET /vehicle-database-test-results/get-restraint-info/{vehicle_no}/{test_no}/{occupant_location}
GET /vehicle-database-test-results/get-intrusion-info/{vehicle_no}/{test_no}
GET /vehicle-database-test-results/get-instrumentation-info/{test_no}?pageNumber={page_number}&count={count}
GET /vehicle-database-test-results/get-instrumentation-detail-info/{curve_no}/{test_no}
```

Assets:

```text
GET /vehicle-database-test-results/get-multimedia-files/{test_no}
GET /vehicle-documents/test-no/{test_no}
```

각 endpoint별 metadata를 문서 표와 코드 상수에 둔다.

```text
name
path_template
endpoint_group
required_for_baseline
is_paginated
path_keys
query_keys
allow_empty
parser_name
notes
```

## Source anomalies 문서화

`docs/2026-04-28__source-contract__current__source-anomalies.md`에 반드시 포함:

### Wrong summary links

- summary response의 `barrierInformation` link가 실제 barrier endpoint가 아니라 vehicle-info endpoint를 가리킬 수 있다.
- 수집기는 summary link를 따라가기보다 endpoint template과 discovered key로 호출한다.

### Pagination

- instrumentation endpoint는 pageNumber/count 기반 pagination.
- `nextUrl`, `total`, `count`, `pageNumber`를 raw provenance에 저장.
- `nextUrl` 누락 가능성을 대비해 누적 count와 total도 비교.

### Empty endpoint

- intrusion, barrier, occupant detail, restraint detail 등은 정상 응답이면서 empty results일 수 있다.
- empty는 failure가 아니다.
- `source_payloads`, `source_payload_sections`에 empty 상태를 기록한다.

### Multi-vehicle / impactor-as-vehicle

- 한 test_no에 vehicle row가 2개 이상일 수 있다.
- `NHTSA DEFORMABLE IMPACTOR` 같은 impactor가 vehicle row로 들어올 수 있다.
- `test_participants`로 일반화한다.

### Date anomalies

- legacy data에는 invalid/partial date가 있을 수 있다.
- raw date와 parsed date를 분리한다.

### Zero vs null

- injury metric `0`은 실제 값일 수 있다.
- `0`, `'0'`, `null`, missing은 모두 다르게 보존한다.

### Media/documents

- photos가 null일 수 있다.
- report/video/document/data package URL은 저장하되 실제 다운로드하지 않는다.

## Field alias map

`docs/2026-04-28__source-contract__current__source-field-aliases.md` 및 `field_aliases.py` 초안:

```text
TEST.TSTNO                    -> tests.test_no
TEST.TSTDAT                   -> tests.test_date_raw
TEST.TSTPRFD                  -> tests.test_performer
TEST.TSTCFND                  -> tests.test_configuration
TEST.CLSSPD                   -> tests.closing_speed_raw / closing_speed

VEHICLE.MAKED                 -> vehicles.make
VEHICLE.MODELD                -> vehicles.model
VEHICLE.YEAR                  -> vehicles.model_year
VEHICLE.VEHSPD                -> vehicles.vehicle_speed_raw / vehicle_speed
VEHICLE.DPD1..DPD6            -> deformation_measurements
VEHICLE.DAMDST                -> deformation_measurements
VEHICLE.CRHDST                -> deformation_measurements
VEHICLE.PDOF                  -> deformation_measurements
VEHICLE.VDI                   -> deformation_measurements

BARRIER.BARRIGD               -> barriers.rigidity
BARRIER.BARSHPD               -> barriers.shape
BARRIER.BARANG                -> barriers.angle_raw / angle

OCCUPANT.OCCLOC               -> occupants.occupant_location_raw
OCCUPANT.OCCTYPD              -> occupants.occupant_type
OCCUPANT.HIC                  -> injury_metrics(metric_code='HIC')
OCCUPANT.CSI                  -> injury_metrics(metric_code='CSI')
OCCUPANT.TTI                  -> injury_metrics(metric_code='TTI')
OCCUPANT.LFEM/RFEM            -> injury_metrics(metric_code='LFEM'/'RFEM')
OCCUPANT.LBELT/SBELT          -> injury_metrics(metric_code='LBELT'/'SBELT')

API.testNo                    -> tests.test_no
API.testDate                  -> tests.test_date_raw
API.testType                  -> tests.test_type
API.testConfiguration         -> tests.test_configuration
API.closingSpeed              -> tests.closing_speed
API.vehicleMake               -> vehicles.make
API.vehicleModel              -> vehicles.model
API.modelYear                 -> vehicles.model_year
API.rigidOrDeformableBarrier  -> barriers.rigidity
API.barrierShape              -> barriers.shape
API.sensorType                -> instrumentation_channels.sensor_type
API.axisDirofSensor           -> instrumentation_channels.sensor_axis
API.inflationer/BeltPretensionerDeployment -> restraints.deployment_status
```

## Catalog builder contract

필수 CLI contract:

```powershell
python -m nhtsa_metadata.cli catalog discover --max-pages 1
python -m nhtsa_metadata.cli catalog collect-test --test-no 10001 --endpoint-set all --paginate-instrumentation
python -m nhtsa_metadata.cli catalog collect --manifest tests/fixtures/live_sample_manifest.csv
python -m nhtsa_metadata.cli catalog rebuild --test-no 10001
python -m nhtsa_metadata.cli coverage report
```

필수 option:

```text
--dry-run
--database-url
--source fixture|live
--allow-live
--endpoint-set summary|metadata|detail|assets|all
--paginate-instrumentation
--save-fixture
--stop-on-source-conflict
--allow-empty-endpoints
--retry-count
--timeout-seconds
--rate-limit-delay-seconds
--resume
--max-pages
--max-items
```

## Filtering contract

필수 facet:

```text
test_type
test_configuration
vehicle_make
vehicle_model
model_year
closing_speed_range
impact_angle
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
injury_metric_range
deformation_code
asset_kind
has_uds_or_tdms_package
```

복합 필터는 v1에서 “같은 test 안에 모든 조건이 존재”하는 AND semantics로 둔다. 같은 occupant/vehicle scoped filter는 v2로 분리 가능하다.

## Field coverage contract

상태값:

```text
mapped
mapped_to_extra_json
unmapped
ignored_by_policy
conflict
```

coverage report 최소 출력:

```text
endpoint_name
section_name
field_path
observed_type
seen_count
non_null_count
mapping_status
mapped_table
mapped_column
example_values
```

## Source code skeleton

생성:

```text
src/nhtsa_metadata/sources/nhtsa_crash/endpoints.py
src/nhtsa_metadata/sources/nhtsa_crash/contracts.py
src/nhtsa_metadata/sources/nhtsa_crash/client.py
src/nhtsa_metadata/sources/nhtsa_crash/fixtures.py
```

`EndpointDefinition` 필수 field:

```python
name: str
path_template: str
endpoint_group: str
is_paginated: bool = False
default_count: int | None = None
requires_test_no: bool = True
requires_vehicle_no: bool = False
requires_occupant_location: bool = False
requires_curve_no: bool = False
allow_empty: bool = True
parser_name: str
```

`contracts.py`:

```text
ApiPagination
ApiMeta
SourceRequest
SourceFetchResult
```

`client.py`:

```text
SourceClientProtocol
FixtureNhtsaClient skeleton
LiveNhtsaClient skeleton; actual HTTP는 Phase 7
```

## Harness update

`.harness/run.ps1`에 필수 문서 존재 확인 추가.

## 테스트

```text
tests/test_source_endpoint_contract.py
tests/test_docs_contract.py
```

검증:

- 필수 endpoint name 존재.
- instrumentation endpoint가 paginated.
- `test_detail` optional core endpoint 존재.
- asset endpoints 존재.
- endpoint path rendering이 URL encoding 수행.
- `--source live` 없이 live client 생성 불가.
- 필수 문서 존재.

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
endpoint matrix가 문서와 코드 상수 양쪽에 존재
source anomaly가 문서화됨
live 호출 안전장치 skeleton 존재
기본 테스트는 외부 네트워크를 사용하지 않음
```
