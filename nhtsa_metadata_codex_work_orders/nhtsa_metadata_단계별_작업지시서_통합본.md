# `nhtsa_metadata` Codex 작업지시서 색인

## 목적

이 문서 세트는 `D:\vscode\nhtsa_metadata` 프로젝트를 Codex에 단계적으로 구현시키기 위한 실행 지시서다. 목표는 **NHTSA Vehicle Crash Test Database metadata-only catalog DB** 구축이다.

최상위 원칙:

> `metadata/{testNo}`는 원천 중 하나일 뿐이며, 완전한 DB는 test_no별 endpoint matrix 전체를 raw-first로 수집한 뒤 canonical/detail/read-model로 재구성한다.

## 사용 순서

1. `11_Codex_Master_Prompt.md`를 먼저 Codex에 제공한다.
2. Phase 0부터 Phase 8까지 순차 구현한다.
3. 각 phase 완료 후 해당 phase의 acceptance criteria와 기본 검증 명령을 통과해야 다음 phase로 진행한다.
4. 기본 검증에서는 live NHTSA API 호출을 금지한다.
5. live validation은 Phase 7의 별도 수동 명령으로만 수행한다.

## 파일 목록

| 순서 | 파일 | 목적 |
|---:|---|---|
| 00 | `00_작업지시서_색인.md` | 전체 사용법과 공통 원칙 |
| 01 | `01_최종_플랜_점검.md` | 최종 플랜 보정 사항 |
| 02 | `02_Phase_0_Scaffold.md` | 프로젝트 skeleton, tooling, harness |
| 03 | `03_Phase_1_Source_Contract.md` | endpoint matrix, anomaly, source contract |
| 04 | `04_Phase_2_DB_Foundation.md` | SQLAlchemy/Alembic schema |
| 05 | `05_Phase_3_Fixtures.md` | fixture/mock 데이터 |
| 06 | `06_Phase_4_Parser_Normalizer.md` | parser, DTO, mapper, field catalog |
| 07 | `07_Phase_5_Ingestion_Rebuild.md` | collect, upsert, rebuild |
| 08 | `08_Phase_6_Query_Filter_API.md` | FastAPI 조회 및 filter API |
| 09 | `09_Phase_7_Manual_Live_Validation.md` | 수동 live 검증 |
| 10 | `10_Phase_8_Scale_Readiness.md` | scale/readiness/PostgreSQL 조건 |
| 11 | `11_Codex_Master_Prompt.md` | Codex에 붙여넣을 master prompt |
| 12 | `12_Global_Acceptance_Checklist.md` | 전체 최종 검수 checklist |

## 공통 금지 사항

- 기본 `pytest`, `scripts/verify.ps1`, `.harness/run.ps1`에서 외부 NHTSA API 호출 금지.
- 사진, 영상, report, UDS, TDMS, ABF, ISO, zip 파일 실제 다운로드 금지.
- `metadata/{testNo}` 단일 endpoint를 완전 DB로 간주 금지.
- summary response의 link 문자열을 endpoint discovery의 단일 근거로 사용 금지.
- `.git`, `.venv`, 기존 DB, `data/manual`, cache, screenshots, response dumps 복사 금지.
- unknown field 폐기 금지.

## 공통 보장 사항

- endpoint별 raw payload 보존.
- 모든 canonical row는 source payload와 JSON path로 역추적 가능.
- 날짜, 숫자, 단위는 raw와 parsed 분리.
- `0`, `'0'`, `null`, missing, empty string은 서로 다르게 보존.
- multi-vehicle, impactor-as-vehicle, empty endpoint, invalid/partial date, wrong summary link, pagination을 v1 기본 전제로 처리.
- fixture/mock 검증과 manual live validation 분리.

## 기본 검증 명령

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check src tests
.venv\Scripts\python.exe -m mypy src\nhtsa_metadata
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
powershell -ExecutionPolicy Bypass -File .harness\run.ps1
```

## 수동 live 검증 명령

Phase 7 이후에만 사용한다. 기본 verify에는 넣지 않는다.

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog collect --manifest tests\fixtures\live_sample_manifest.csv --database-url sqlite:///data/live_validation.sqlite --source live --allow-live --endpoint-set all --paginate-instrumentation
.venv\Scripts\python.exe -m nhtsa_metadata.cli coverage report --database-url sqlite:///data/live_validation.sqlite
.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog assert-live-baseline --database-url sqlite:///data/live_validation.sqlite
```


---

# 최종 플랜 점검 및 보정 사항

## 판정

첨부 최종 플랜은 프로젝트 방향, metadata-only scope, source-first 원칙, raw/provenance 계층, canonical/detail/read-model 계층, live validation 분리 방식이 적절하다. 단, Codex 구현 지시서에는 아래 보정 사항을 반영한다.

## 보정 1 — Endpoint matrix에 `get-test-detail/{testNo}` 추가

공식 OpenAPI에는 `test-no/{testNo}`, `metadata/{testNo}` 외에도 `get-test-detail/{testNo}`가 존재한다. v1에서는 optional core endpoint로 등록한다.

```text
source_endpoints.name = test_detail
path_template = /vehicle-database-test-results/get-test-detail/{test_no}
endpoint_group = core_optional
required_for_baseline = false
allow_empty = true
```

## 보정 2 — `files` 대신 `media_assets`로 명칭 통일

최종 구현에서는 asset registry table을 `media_assets`로 통일한다. `files`는 이전 플랜의 잔여 표현으로만 취급한다.

필수 asset kind:

```text
photo
video
report
document
data_package
zip
uds
abf
iso
tdms
other
```

## 보정 3 — Live API 호출 이중 안전장치

manual live command라 하더라도 다음 둘을 모두 요구한다.

```text
--source live
--allow-live
```

선택적으로 환경변수도 지원한다.

```text
NHTSA_METADATA_ALLOW_LIVE=1
```

테스트에서는 `--allow-live` 누락 시 live client가 생성되지 않는 것을 확인한다.

## 보정 4 — `source_payloads`와 관측 이력 분리

반복 수집 시 동일 payload를 중복 저장하지 않으면서 run provenance를 유지하려면 다음 구조가 안전하다.

```text
source_payloads
  - immutable unique payload store
  - unique(endpoint_name, canonical_url_hash, payload_hash)

source_payload_observations
  - each fetch observation
  - run_id, run_item_id, source_payload_id, observed_at, elapsed_ms, http_status
```

## 보정 5 — Pagination completeness를 endpoint별로 저장

`get-instrumentation-info/{testNo}`는 paginated endpoint다. 수집기는 `nextUrl`이 있거나 누적 count가 total보다 작으면 반복 수집해야 한다.

저장 기준:

```text
source_payloads.page_number
source_payloads.count_returned
source_payloads.total_available
source_payloads.pagination_json
collection_run_items.endpoint_statuses_json
```

## 보정 6 — Fixture는 실제 shape + synthetic volume 조합 허용

10001 instrumentation 634건을 모두 fixture로 저장해도 되지만 repository 크기가 커질 수 있다. 다음 중 하나를 허용한다.

- 실제 JSON fixture를 여러 page로 저장.
- compact seed에서 634건을 deterministic하게 생성.

단, parser/ingestion/read-model 테스트는 아래 위험을 반드시 재현한다.

```text
legacy metadata export
zero-valued injury metrics
modern frontal NCAP
multi-vehicle side impact
impactor-as-vehicle
empty barrier/intrusion endpoint
instrumentation pagination
media/document/data package asset registry
```

## 보정 7 — `test_participants`는 v1 필수

10003처럼 deformable impactor가 vehicle row로 들어오는 경우가 있다. 차량/장벽만으로 억지 모델링하지 말고 `test_participants`를 둔다.

```text
subject_vehicle
impactor_vehicle
barrier
sled
other
unknown
```

보수적 분류 규칙:

```text
vehicleMake == 'NHTSA' and vehicleModel contains 'IMPACTOR' -> impactor_vehicle
barrier row exists -> barrier participant 추가
그 외 vehicle row -> subject_vehicle 기본값
불명확하면 unknown 또는 other + raw_row_json 보존
```

## 보정 8 — Read model은 canonical의 파생물

`test_filter_summary`, `test_facets`, `asset_summary`, `field_coverage_snapshots`는 source of truth가 아니다. 항상 raw/canonical에서 rebuild 가능해야 한다.

## 보정 9 — API default response에는 raw payload 전문 제외

`GET /api/tests/{test_no}`는 canonical detail과 asset registry를 반환하되 raw payload 전문은 기본 제외한다. raw는 별도 endpoint 또는 `include_raw` 옵션으로 분리한다.

## 보정 10 — 완료 기준은 재처리 가능성

최종 완료 기준:

```text
fixture collect -> canonical row 생성
동일 fixture collect 재실행 -> canonical row count 증가 없음
source_payloads에서 rebuild -> 동일 canonical/read-model 결과
coverage report -> mapped/unmapped field 확인 가능
manual live validation -> baseline 통과 또는 미수행 사실 명시
```

## 구현 제외 확정

- UI
- 다운로드 실행
- queue worker
- progress API
- waveform 분석
- TDMS/UDS/ABF/ISO parsing
- 대규모 full crawl 자동화
- production deployment


---

# Phase 0 — Scaffold 작업지시서

## 목표

`D:\vscode\nhtsa_metadata`에 독립 Python 프로젝트 skeleton을 생성한다. 이 phase에서는 실제 NHTSA 수집을 구현하지 않는다. 목표는 패키지, 개발 도구, harness, 기본 FastAPI app, 기본 CLI가 실행 가능한 상태를 만드는 것이다.

## 전제

- 작업 루트: `D:\vscode\nhtsa_metadata`
- 패키지명: `nhtsa_metadata`
- stack: Python + FastAPI + SQLite + SQLAlchemy + Alembic
- UI 없음
- live API 호출 없음
- 기존 `nhtsa_gui`가 있으면 구조만 read-only로 참조한다.
- 기존 `.git`, `.venv`, DB, `data/manual`, cache, screenshots, response dumps는 복사하지 않는다.

## 생성할 구조

```text
D:\vscode\nhtsa_metadata
├── AGENTS.md
├── 2026-05-02__classifier-v1-4-failure-package__recorded__v1-4-full-corpus-failure-package.md
├── pyproject.toml
├── alembic.ini
├── .env.example
├── .gitignore
├── .agent\project.json
├── .agents\skills\project-kickoff\
├── .agents\skills\project-verify\
├── .harness\run.ps1
├── .vscode\settings.json
├── scripts\test.ps1
├── scripts\verify.ps1
├── docs\2026-04-28__operations__current__operations.md
├── docs\phase_reports\.gitkeep
├── instructions\.gitkeep
├── src\nhtsa_metadata\
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── config.py
│   ├── api\__init__.py
│   ├── api\app.py
│   ├── db\__init__.py
│   ├── db\base.py
│   ├── db\models.py
│   ├── db\session.py
│   ├── services\__init__.py
│   └── sources\nhtsa_crash\__init__.py
└── tests\
    ├── __init__.py
    ├── conftest.py
    ├── test_smoke.py
    └── fixtures\nhtsa\.gitkeep
```

## `pyproject.toml`

권장 runtime dependency:

```toml
[project]
name = "nhtsa-metadata"
version = "0.1.0"
description = "Metadata-only NHTSA crash test catalog DB"
requires-python = ">=3.11,<3.14"
dependencies = [
  "fastapi>=0.110",
  "uvicorn[standard]>=0.27",
  "sqlalchemy>=2.0",
  "alembic>=1.13",
  "pydantic>=2.6",
  "pydantic-settings>=2.2",
  "httpx>=0.27",
  "typer>=0.12",
  "rich>=13.7",
  "python-dotenv>=1.0",
]
```

Dev dependency:

```toml
[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "pytest-cov>=5.0",
  "ruff>=0.5",
  "mypy>=1.10",
  "respx>=0.21",
]
```

Tooling:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
  "live: tests that call live NHTSA services; never run in default verify",
]

[tool.ruff]
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.mypy]
python_version = "3.11"
packages = ["nhtsa_metadata"]
warn_unused_ignores = true
warn_return_any = true
no_implicit_optional = true
```

## `.gitignore`

반드시 제외:

```gitignore
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
*.sqlite
*.sqlite3
data/
!data/.gitkeep
.env
.env.*
!.env.example
node_modules/
.next/
screenshots/
response_dumps/
```

## `config.py`

Pydantic Settings를 사용한다.

```python
class Settings(BaseSettings):
    app_name: str = "nhtsa_metadata"
    environment: str = "local"
    database_url: str = "sqlite:///data/nhtsa_metadata.sqlite"
    nhtsa_base_url: str = "https://nrd.api.nhtsa.dot.gov/nhtsa/vehicle/api/v1"
    allow_live: bool = False
    default_timeout_seconds: float = 30.0
    default_retry_count: int = 2
    rate_limit_delay_seconds: float = 0.0
```

주의:

- 기본값 `allow_live=False`.
- test 환경에서는 tmp DB URL 주입 가능.
- DB URL 출력 시 credential이 포함될 경우 sanitize한다.

## FastAPI app

`src/nhtsa_metadata/api/app.py`:

```python
def create_app(settings: Settings | None = None) -> FastAPI:
    ...
```

Phase 0 `/api/health` 최소 응답:

```json
{
  "status": "ok",
  "app": "nhtsa_metadata",
  "environment": "local",
  "database_url_configured": true
}
```

## CLI

Typer 기반.

필수 명령:

```powershell
python -m nhtsa_metadata.cli version
python -m nhtsa_metadata.cli health
python -m nhtsa_metadata
```

`__main__.py`는 CLI app을 호출한다.

## Scripts

`scripts/test.ps1`:

```powershell
$ErrorActionPreference = "Stop"
.venv\Scripts\python.exe -m pytest -q
```

`scripts/verify.ps1`:

```powershell
$ErrorActionPreference = "Stop"
.venv\Scripts\python.exe -m ruff check src tests
.venv\Scripts\python.exe -m mypy src\nhtsa_metadata
.venv\Scripts\python.exe -m pytest -q
```

`.harness/run.ps1`:

- `scripts/verify.ps1` 호출.
- live API 호출 없음.
- Phase 1 이후 문서 존재 여부 검사 확장.

## `AGENTS.md`

반드시 포함:

```text
- metadata-only NHTSA crash test catalog DB
- 다운로드 실행, waveform 분석, UI는 v0 범위 아님
- 기본 verify/harness에서 live API 호출 금지
- live API는 manual validation 명령과 --allow-live가 있을 때만 허용
- 기존 nhtsa_gui/nhtsa 경로는 read-only reference
- .git, .venv, DB, data/manual, cache, screenshots, response dumps 복사 금지
```

## `2026-05-02__classifier-v1-4-failure-package__recorded__v1-4-full-corpus-failure-package.md`

섹션:

```text
Purpose
Scope
Not in Scope
Setup
Verification
Manual Live Validation
Project Layout
```

Phase 0에서는 Manual Live Validation을 “Phase 7에서 구현”이라고 적어도 된다.

## 테스트

`tests/test_smoke.py`:

- `import nhtsa_metadata` 성공.
- `create_app()` 성공.
- `/api/health` test client 호출 성공.
- CLI app import 성공.

`tests/conftest.py`:

- tmp DB URL fixture skeleton.
- live marker가 default로 실행되지 않는다는 주석.

## 완료 기준

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check src tests
.venv\Scripts\python.exe -m mypy src\nhtsa_metadata
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
powershell -ExecutionPolicy Bypass -File .harness\run.ps1
```

## Phase report

`docs/phase_reports/2026-04-28__bootstrap-phase-0__pass__phase-0-report.md` 생성:

```markdown
# Phase 0 Report

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


---

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


---

# Phase 2 — DB Foundation 작업지시서

## 목표

SQLAlchemy/Alembic 기반으로 raw/provenance, canonical core, filter/read-model schema를 구축한다. Parser와 ingestion full logic은 Phase 4/5에서 구현하되, 이 phase에서는 migration, model import, 기본 repository test가 통과해야 한다.

## 설계 원칙

1. FK는 내부 integer PK를 사용한다.
2. 외부 natural key(`test_no`, `vehicle_no`, `curve_no`)는 unique/index로 관리한다.
3. raw payload는 immutable store다.
4. canonical row는 lineage columns를 가진다.
5. read model은 canonical에서 rebuild 가능한 파생물이다.
6. SQLite로 시작하지만 PostgreSQL 이전을 방해하지 않는다.

## 생성/수정 파일

```text
alembic.ini
alembic/env.py
alembic/versions/0001_initial_schema.py
src/nhtsa_metadata/db/base.py
src/nhtsa_metadata/db/models.py
src/nhtsa_metadata/db/session.py
src/nhtsa_metadata/db/migrations.py
src/nhtsa_metadata/services/db_health.py
docs/2026-04-28__schema__current__db-schema.md
docs/phase_reports/2026-04-28__bootstrap-phase-2__pass__phase-2-report.md
tests/test_db_migrations.py
tests/test_db_models.py
```

## 공통 column 정책

### Timestamp

모든 주요 table:

```text
created_at DATETIME NOT NULL
updated_at DATETIME NULL
```

### JSON

SQLAlchemy `JSON` 사용. SQLite에서는 text storage가 되더라도 model API는 dict/list로 동작해야 한다.

### Hash

```text
payload_hash         SHA-256 hex, length 64
source_row_hash      SHA-256 hex, length 64
canonical_url_hash   SHA-256 hex, length 64
```

### Canonical lineage mixin

canonical table에는 다음 columns를 둔다.

```text
source_payload_id       FK source_payloads.id NULL
source_endpoint_name    TEXT NULL
source_section_name     TEXT NULL
source_row_path         TEXT NULL
source_row_hash         TEXT NULL
raw_row_json            JSON NULL
extra_json              JSON NULL
```

## Raw / Provenance layer

### `collection_runs`

목적: 수집 실행 단위.

핵심 columns:

```text
id PK
run_uuid TEXT UNIQUE NOT NULL
run_type TEXT NOT NULL                 # discover, collect, collect_test, rebuild, live_validation
mode TEXT NOT NULL                     # fixture, live, rebuild
status TEXT NOT NULL                   # running, succeeded, failed, partial, dry_run
input_manifest_path TEXT NULL
input_manifest_hash TEXT NULL
input_range_json JSON NULL
database_url_sanitized TEXT NULL
endpoint_set TEXT NULL
include_detail_endpoints BOOLEAN NOT NULL DEFAULT 0
paginate_instrumentation BOOLEAN NOT NULL DEFAULT 0
dry_run BOOLEAN NOT NULL DEFAULT 0
allow_live BOOLEAN NOT NULL DEFAULT 0
retry_count INTEGER NOT NULL DEFAULT 0
timeout_seconds NUMERIC NULL
rate_limit_delay_seconds NUMERIC NULL
success_count INTEGER NOT NULL DEFAULT 0
failure_count INTEGER NOT NULL DEFAULT 0
skipped_count INTEGER NOT NULL DEFAULT 0
started_at DATETIME NOT NULL
ended_at DATETIME NULL
software_version TEXT NULL
extra_json JSON NULL
created_at DATETIME NOT NULL
updated_at DATETIME NULL
```

Indexes:

```text
idx_collection_runs_started_at
idx_collection_runs_status
```

### `collection_run_items`

목적: test_no별 수집 상태.

```text
id PK
run_id FK collection_runs.id NOT NULL
test_no INTEGER NOT NULL
status TEXT NOT NULL                   # pending, running, succeeded, failed, skipped, partial
attempt_count INTEGER NOT NULL DEFAULT 0
started_at DATETIME NULL
ended_at DATETIME NULL
last_error_type TEXT NULL
last_error_message TEXT NULL
endpoints_attempted_json JSON NULL
endpoints_succeeded_json JSON NULL
endpoints_failed_json JSON NULL
endpoint_statuses_json JSON NULL
extra_json JSON NULL
created_at DATETIME NOT NULL
updated_at DATETIME NULL
```

Unique:

```text
unique(run_id, test_no)
```

### `source_endpoints`

목적: endpoint template catalog.

```text
id PK
name TEXT UNIQUE NOT NULL
endpoint_group TEXT NOT NULL           # discovery, core, core_optional, detail, assets
method TEXT NOT NULL DEFAULT 'GET'
path_template TEXT NOT NULL
is_paginated BOOLEAN NOT NULL DEFAULT 0
default_count INTEGER NULL
requires_test_no BOOLEAN NOT NULL DEFAULT 1
requires_vehicle_no BOOLEAN NOT NULL DEFAULT 0
requires_occupant_location BOOLEAN NOT NULL DEFAULT 0
requires_curve_no BOOLEAN NOT NULL DEFAULT 0
allow_empty BOOLEAN NOT NULL DEFAULT 1
required_for_baseline BOOLEAN NOT NULL DEFAULT 0
parser_name TEXT NOT NULL
enabled BOOLEAN NOT NULL DEFAULT 1
notes TEXT NULL
extra_json JSON NULL
created_at DATETIME NOT NULL
updated_at DATETIME NULL
```

Seed는 migration 또는 idempotent bootstrap에서 넣는다. 권장: migration seed.

### `source_payloads`

목적: immutable raw payload store.

```text
id PK
endpoint_id FK source_endpoints.id NULL
endpoint_name TEXT NOT NULL
source TEXT NOT NULL DEFAULT 'nhtsa_crash'
test_no INTEGER NULL
vehicle_no INTEGER NULL
occupant_location_raw TEXT NULL
curve_no INTEGER NULL
page_number INTEGER NULL
request_url TEXT NOT NULL
canonical_url_hash TEXT NOT NULL
http_status INTEGER NULL
api_status INTEGER NULL
api_message TEXT NULL
api_error TEXT NULL
pagination_json JSON NULL
count_returned INTEGER NULL
total_available INTEGER NULL
payload_hash TEXT NOT NULL
payload_json JSON NOT NULL
fetched_at DATETIME NOT NULL
created_at DATETIME NOT NULL
updated_at DATETIME NULL
```

Unique:

```text
unique(endpoint_name, canonical_url_hash, payload_hash)
```

Indexes:

```text
idx_source_payloads_test_no
idx_source_payloads_endpoint_test
idx_source_payloads_payload_hash
idx_source_payloads_fetched_at
```

### `source_payload_observations`

목적: 동일 payload의 반복 관측 이력.

```text
id PK
source_payload_id FK source_payloads.id NOT NULL
run_id FK collection_runs.id NULL
run_item_id FK collection_run_items.id NULL
observed_at DATETIME NOT NULL
http_status INTEGER NULL
elapsed_ms INTEGER NULL
response_size_bytes INTEGER NULL
request_headers_json JSON NULL
response_headers_json JSON NULL
extra_json JSON NULL
created_at DATETIME NOT NULL
```

### `source_payload_sections`

```text
id PK
source_payload_id FK source_payloads.id NOT NULL
section_name TEXT NOT NULL
json_path TEXT NOT NULL
row_count INTEGER NOT NULL DEFAULT 0
section_hash TEXT NULL
sample_json JSON NULL
created_at DATETIME NOT NULL
updated_at DATETIME NULL
```

Unique:

```text
unique(source_payload_id, section_name, json_path)
```

### `source_field_catalog`

```text
id PK
endpoint_name TEXT NOT NULL
section_name TEXT NULL
field_path TEXT NOT NULL
observed_type TEXT NOT NULL
first_seen_at DATETIME NOT NULL
last_seen_at DATETIME NOT NULL
seen_count INTEGER NOT NULL DEFAULT 0
non_null_count INTEGER NOT NULL DEFAULT 0
mapping_status TEXT NOT NULL DEFAULT 'unmapped'
mapped_table TEXT NULL
mapped_column TEXT NULL
example_values_json JSON NULL
created_at DATETIME NOT NULL
updated_at DATETIME NULL
```

Unique:

```text
unique(endpoint_name, section_name, field_path)
```

### `source_conflicts`

```text
id PK
test_no INTEGER NOT NULL
field_semantic_key TEXT NOT NULL
canonical_table TEXT NULL
canonical_column TEXT NULL
endpoint_a TEXT NOT NULL
source_payload_id_a FK source_payloads.id NULL
value_a_json JSON NULL
endpoint_b TEXT NOT NULL
source_payload_id_b FK source_payloads.id NULL
value_b_json JSON NULL
resolution_status TEXT NOT NULL DEFAULT 'unresolved'
resolved_value_json JSON NULL
notes TEXT NULL
created_at DATETIME NOT NULL
updated_at DATETIME NULL
```

### `canonical_row_sources`

```text
id PK
canonical_table TEXT NOT NULL
canonical_id INTEGER NOT NULL
source_payload_id FK source_payloads.id NOT NULL
source_endpoint_name TEXT NOT NULL
source_section_name TEXT NULL
source_row_path TEXT NULL
source_row_hash TEXT NULL
created_at DATETIME NOT NULL
```

Indexes:

```text
idx_canonical_row_sources_table_id
idx_canonical_row_sources_payload
```

## Canonical core layer

### `tests`

핵심 columns:

```text
id PK
test_no INTEGER UNIQUE NOT NULL
test_reference_no TEXT NULL
test_type TEXT NULL
test_title TEXT NULL
contractor_study_title TEXT NULL
test_performer TEXT NULL
contract_number TEXT NULL
test_objective TEXT NULL
test_configuration TEXT NULL
test_configuration_key TEXT NULL
impact_angle_raw TEXT NULL
impact_angle NUMERIC NULL
offset_distance_raw TEXT NULL
offset_distance NUMERIC NULL
closing_speed_raw TEXT NULL
closing_speed NUMERIC NULL
closing_speed_unit_raw TEXT NULL
closing_speed_parse_status TEXT NOT NULL DEFAULT 'missing'
measured_unit_raw TEXT NULL
total_curve_count_raw TEXT NULL
total_curve_count INTEGER NULL
test_date_raw TEXT NULL
test_date DATE NULL
test_year INTEGER NULL
test_month INTEGER NULL
test_day INTEGER NULL
test_date_parse_status TEXT NOT NULL DEFAULT 'missing'
test_date_source_endpoint TEXT NULL
track_condition TEXT NULL
<lineage columns>
created_at DATETIME NOT NULL
updated_at DATETIME NULL
```

Indexes:

```text
idx_tests_test_type
idx_tests_test_configuration
idx_tests_test_date
idx_tests_closing_speed
```

### `vehicles`

```text
id PK
test_id FK tests.id NOT NULL
source_vehicle_no INTEGER NOT NULL
make TEXT NULL
model TEXT NULL
model_year INTEGER NULL
vin TEXT NULL
body_type TEXT NULL
engine_type TEXT NULL
transmission TEXT NULL
drive_type TEXT NULL
vehicle_test_weight_raw TEXT NULL
vehicle_test_weight NUMERIC NULL
vehicle_length_raw TEXT NULL
vehicle_length NUMERIC NULL
vehicle_width_raw TEXT NULL
vehicle_width NUMERIC NULL
vehicle_speed_raw TEXT NULL
vehicle_speed NUMERIC NULL
vax_crush_distance_raw TEXT NULL
vax_crush_distance NUMERIC NULL
<lineage columns>
```

Unique: `unique(test_id, source_vehicle_no)`

Indexes: `idx_vehicles_make_model_year`, `idx_vehicles_test_id`

### `barriers`

```text
id PK
test_id FK tests.id NOT NULL
rigidity TEXT NULL
shape TEXT NULL
barrier_type TEXT NULL
angle_raw TEXT NULL
angle NUMERIC NULL
diameter_raw TEXT NULL
diameter NUMERIC NULL
barrier_commentary TEXT NULL
source_barrier_no TEXT NULL
<lineage columns>
```

Unique: `unique(test_id, source_row_hash)`

### `test_participants`

```text
id PK
test_id FK tests.id NOT NULL
participant_kind TEXT NOT NULL      # subject_vehicle, impactor_vehicle, barrier, sled, other, unknown
vehicle_id FK vehicles.id NULL
barrier_id FK barriers.id NULL
source_vehicle_no INTEGER NULL
display_name TEXT NULL
classification_reason TEXT NULL
<lineage columns>
```

Service-level idempotency로 `(test_id, participant_kind, vehicle_id, barrier_id, source_vehicle_no)` 중복을 막는다.

### `occupants`

```text
id PK
test_id FK tests.id NOT NULL
vehicle_id FK vehicles.id NULL
source_vehicle_no INTEGER NULL
occupant_location_raw TEXT NOT NULL
occupant_location_normalized TEXT NULL
seat_position TEXT NULL
occupant_type TEXT NULL
dummy_type TEXT NULL
sex TEXT NULL
size_percentile TEXT NULL
age_raw TEXT NULL
age NUMERIC NULL
height_raw TEXT NULL
height NUMERIC NULL
weight_raw TEXT NULL
weight NUMERIC NULL
contact_points_json JSON NULL
<lineage columns>
```

Unique: `unique(test_id, source_vehicle_no, occupant_location_raw, source_row_hash)`

### `restraints`

```text
id PK
test_id FK tests.id NOT NULL
vehicle_id FK vehicles.id NULL
occupant_id FK occupants.id NULL
source_vehicle_no INTEGER NULL
occupant_location_raw TEXT NULL
restraint_type TEXT NULL
restraint_type_raw TEXT NULL
restraint_location TEXT NULL
mounting_location TEXT NULL
manufacturer TEXT NULL
model TEXT NULL
deployment_status TEXT NULL
deployment_raw TEXT NULL
pretensioner_deployment TEXT NULL
airbag_stage TEXT NULL
commentary TEXT NULL
<lineage columns>
```

Unique: `unique(test_id, source_vehicle_no, occupant_location_raw, restraint_type_raw, deployment_raw, source_row_hash)`

### `instrumentation_channels`

```text
id PK
test_id FK tests.id NOT NULL
vehicle_id FK vehicles.id NULL
occupant_id FK occupants.id NULL
curve_no INTEGER NOT NULL
channel_no TEXT NULL
sensor_type TEXT NULL
sensor_location TEXT NULL
sensor_attachment TEXT NULL
sensor_axis TEXT NULL
axis_direction_raw TEXT NULL
unit_raw TEXT NULL
engineering_unit TEXT NULL
data_status TEXT NULL
channel_status TEXT NULL
filter_class TEXT NULL
sample_rate_raw TEXT NULL
sample_rate NUMERIC NULL
time_increment_raw TEXT NULL
time_increment NUMERIC NULL
first_point_raw TEXT NULL
first_point NUMERIC NULL
last_point_raw TEXT NULL
last_point NUMERIC NULL
commentary TEXT NULL
<lineage columns>
```

Unique: `unique(test_id, curve_no)`

Indexes: sensor_type, sensor_location, sensor_axis, engineering_unit.

### `instrumentation_channel_details`

```text
id PK
instrumentation_channel_id FK instrumentation_channels.id NULL
test_id FK tests.id NOT NULL
curve_no INTEGER NOT NULL
detail_key TEXT NOT NULL
detail_value_raw TEXT NULL
detail_value_numeric NUMERIC NULL
unit_raw TEXT NULL
parse_status TEXT NOT NULL DEFAULT 'missing'
<lineage columns>
```

### `injury_metrics`

Long-form metric table.

```text
id PK
test_id FK tests.id NOT NULL
vehicle_id FK vehicles.id NULL
occupant_id FK occupants.id NULL
metric_code TEXT NOT NULL
metric_name TEXT NULL
metric_family TEXT NULL
metric_context TEXT NULL
raw_value TEXT NULL
numeric_value NUMERIC NULL
unit_raw TEXT NULL
parse_status TEXT NOT NULL DEFAULT 'missing'
<lineage columns>
```

Unique: `unique(test_id, occupant_id, metric_code, metric_context, source_row_hash)`

### `deformation_measurements`

```text
id PK
test_id FK tests.id NOT NULL
vehicle_id FK vehicles.id NULL
measurement_family TEXT NOT NULL       # DPD, AX, BX, DAMDST, CRHDST, PDOF, VDI, other
measurement_code TEXT NOT NULL
measurement_index INTEGER NULL
raw_value TEXT NULL
numeric_value NUMERIC NULL
unit_raw TEXT NULL
parse_status TEXT NOT NULL DEFAULT 'missing'
<lineage columns>
```

Unique: `unique(test_id, vehicle_id, measurement_family, measurement_code, measurement_index)`

### `intrusion_measurements`

```text
id PK
test_id FK tests.id NOT NULL
vehicle_id FK vehicles.id NULL
source_vehicle_no INTEGER NULL
location_code_raw TEXT NULL
measurement_code_raw TEXT NOT NULL
measurement_family TEXT NULL
raw_value TEXT NULL
numeric_value NUMERIC NULL
unit_raw TEXT NULL
parse_status TEXT NOT NULL DEFAULT 'missing'
<lineage columns>
```

### `media_assets`

```text
id PK
test_id FK tests.id NOT NULL
asset_kind TEXT NOT NULL
source_url TEXT NOT NULL
canonical_url_hash TEXT NOT NULL
file_ext TEXT NULL
suggested_filename TEXT NULL
content_type TEXT NULL
size_bytes INTEGER NULL
title TEXT NULL
description TEXT NULL
<lineage columns>
```

Unique: `unique(test_id, asset_kind, canonical_url_hash)`

### `code_values`

```text
id PK
code_set TEXT NOT NULL
code_value TEXT NOT NULL
normalized_value TEXT NULL
description TEXT NULL
first_seen_test_id FK tests.id NULL
seen_count INTEGER NOT NULL DEFAULT 0
extra_json JSON NULL
created_at DATETIME NOT NULL
updated_at DATETIME NULL
```

Unique: `unique(code_set, code_value)`

## Read model layer

### `test_filter_summary`

One row per test.

```text
id PK
test_id FK tests.id UNIQUE NOT NULL
test_no INTEGER UNIQUE NOT NULL
test_type TEXT NULL
test_configuration TEXT NULL
test_date DATE NULL
model_year_min INTEGER NULL
model_year_max INTEGER NULL
vehicle_makes_json JSON NULL
vehicle_models_json JSON NULL
participant_kinds_json JSON NULL
barrier_rigidities_json JSON NULL
barrier_shapes_json JSON NULL
occupant_locations_json JSON NULL
dummy_types_json JSON NULL
restraint_types_json JSON NULL
restraint_deployments_json JSON NULL
sensor_types_json JSON NULL
sensor_locations_json JSON NULL
sensor_axes_json JSON NULL
sensor_units_json JSON NULL
injury_metric_codes_json JSON NULL
deformation_codes_json JSON NULL
asset_kinds_json JSON NULL
has_photo BOOLEAN NOT NULL DEFAULT 0
has_video BOOLEAN NOT NULL DEFAULT 0
has_report BOOLEAN NOT NULL DEFAULT 0
has_data_package BOOLEAN NOT NULL DEFAULT 0
has_uds_or_tdms_package BOOLEAN NOT NULL DEFAULT 0
asset_counts_json JSON NULL
summary_json JSON NULL
rebuilt_at DATETIME NOT NULL
created_at DATETIME NOT NULL
updated_at DATETIME NULL
```

### `test_facets`

```text
id PK
test_id FK tests.id NOT NULL
test_no INTEGER NOT NULL
facet_name TEXT NOT NULL
facet_value TEXT NOT NULL
facet_value_normalized TEXT NULL
facet_scope TEXT NULL
source_table TEXT NULL
source_id INTEGER NULL
created_at DATETIME NOT NULL
```

Unique: `unique(test_id, facet_name, facet_value, facet_scope, source_table, source_id)`

Indexes: `idx_test_facets_name_value`, `idx_test_facets_test_name`.

### `asset_summary`

```text
id PK
test_id FK tests.id UNIQUE NOT NULL
test_no INTEGER UNIQUE NOT NULL
photo_count INTEGER NOT NULL DEFAULT 0
video_count INTEGER NOT NULL DEFAULT 0
report_count INTEGER NOT NULL DEFAULT 0
document_count INTEGER NOT NULL DEFAULT 0
data_package_count INTEGER NOT NULL DEFAULT 0
asset_kinds_json JSON NULL
rebuilt_at DATETIME NOT NULL
created_at DATETIME NOT NULL
updated_at DATETIME NULL
```

### `field_coverage_snapshots`

```text
id PK
run_id FK collection_runs.id NULL
snapshot_at DATETIME NOT NULL
total_fields INTEGER NOT NULL
mapped_fields INTEGER NOT NULL
mapped_to_extra_json_fields INTEGER NOT NULL
unmapped_fields INTEGER NOT NULL
ignored_fields INTEGER NOT NULL
conflict_fields INTEGER NOT NULL
by_endpoint_json JSON NULL
created_at DATETIME NOT NULL
```

## SQLAlchemy/Alembic 지침

- SQLAlchemy 2.0 style 사용.
- `Base`는 `src/nhtsa_metadata/db/base.py`.
- model은 우선 `src/nhtsa_metadata/db/models.py`에 둔다.
- `session.py`는 engine/session factory/context manager 제공.
- SQLite file URL parent directory 자동 생성.
- `alembic/env.py`는 `Base.metadata`를 target metadata로 사용.
- `0001_initial_schema.py`는 upgrade/downgrade 모두 구현.
- downgrade는 FK 역순으로 drop.

## `docs/2026-04-28__schema__current__db-schema.md`

다음 포함:

```text
table group 개요
각 table 목적
핵심 column
unique key
index
raw/parsed value policy
lineage policy
rebuild 가능성
```

## 테스트

`tests/test_db_migrations.py`:

- tmp SQLite DB에 Alembic upgrade head.
- 필수 table 목록 존재.
- Alembic downgrade base 가능.

`tests/test_db_models.py`:

- `source_endpoints` seed 또는 insert 가능.
- `tests` row insert 가능.
- `vehicles`가 `tests.id` FK 연결.
- unique constraint 동작.
- JSON column dict 저장/조회 가능.
- canonical model이 lineage columns 보유.

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
Alembic upgrade/downgrade 성공
docs/2026-04-28__schema__current__db-schema.md와 실제 table 목록 일치
canonical tables가 lineage columns 보유
source_payloads payload hash unique 정책 구현
read model tables 존재
```


---

# Phase 3 — Fixtures 작업지시서

## 목표

fixture/mock 기반으로 NHTSA source shape를 재현한다. 기본 test suite에서 live API를 호출하지 않고 legacy, modern, multi-vehicle, pagination, media/document variation을 검증할 수 있어야 한다.

## Fixture 범위

최소 test_no:

```text
10      legacy VTB; metadata export contains TEST/VEHICLE/BARRIER/OCCUPANT
30      legacy NCAP VTB; zero injury metrics; report/video no photos
10001   modern frontal NCAP; 1 vehicle; barrier; 2 occupants; instrumentation/media/data packages
10003   modern side impact; 2 vehicles; impactor-as-vehicle; no barrier endpoint data; instrumentation/media/report
```

Live validation manifest에는 추가로 `1`, `10004`, `10005`도 포함한다.

## 생성할 파일

```text
tests/fixtures/nhtsa/fixture_manifest.json
tests/fixtures/nhtsa/live_sample_manifest.csv

tests/fixtures/nhtsa/metadata_10.json
tests/fixtures/nhtsa/metadata_30.json
tests/fixtures/nhtsa/metadata_10001.json
tests/fixtures/nhtsa/metadata_10003.json

tests/fixtures/nhtsa/test_summary_10001.json
tests/fixtures/nhtsa/test_summary_10003.json

tests/fixtures/nhtsa/vehicle_info_10001.json
tests/fixtures/nhtsa/vehicle_info_10003.json

tests/fixtures/nhtsa/barrier_info_10001.json
tests/fixtures/nhtsa/barrier_info_10003_empty.json

tests/fixtures/nhtsa/occupant_info_10001.json
tests/fixtures/nhtsa/occupant_info_10003.json

tests/fixtures/nhtsa/restraint_info_10001_left_front_seat.json
tests/fixtures/nhtsa/restraint_info_10001_right_front_seat.json

tests/fixtures/nhtsa/intrusion_info_10001_empty.json
tests/fixtures/nhtsa/instrumentation_info_10001_page_0.json
tests/fixtures/nhtsa/instrumentation_info_10001_page_1.json
tests/fixtures/nhtsa/instrumentation_info_10003_page_0.json

tests/fixtures/nhtsa/multimedia_files_10001.json
tests/fixtures/nhtsa/multimedia_files_10003.json
tests/fixtures/nhtsa/vehicle_documents_10001.json
tests/fixtures/nhtsa/vehicle_documents_10003.json
```

일부 fixture는 compact seed + deterministic generator로 대체 가능하다.

```text
tests/fixtures/nhtsa/generated/instrumentation_10001_seed.json
src/nhtsa_metadata/sources/nhtsa_crash/fixture_factory.py
```

## 공통 API-style fixture wrapper

```json
{
  "meta": {
    "pagination": {
      "pageNumber": 0,
      "count": 1,
      "total": 1,
      "currentUrl": "http://...",
      "nextUrl": null,
      "previousUrl": null
    },
    "status": 200,
    "message": "Success",
    "error": ""
  },
  "results": []
}
```

`metadata/{testNo}` export fixture는 실제 shape에 맞춰 `TEST`, `VEHICLE`, `BARRIER`, `OCCUPANT`, `RESTRAINT`, `INSTRUMENTATION`, `URL`, `REPORTS`, `VIDEOS`, `PHOTOS` section을 포함할 수 있다.

## `fixture_manifest.json`

endpoint key와 fixture file을 연결한다.

예:

```json
{
  "tests": {
    "10001": {
      "test_summary": "test_summary_10001.json",
      "metadata_export": "metadata_10001.json",
      "vehicle_info": "vehicle_info_10001.json",
      "barrier_info": "barrier_info_10001.json",
      "occupant_info": "occupant_info_10001.json",
      "restraint_info": {
        "1|LEFT FRONT SEAT": "restraint_info_10001_left_front_seat.json",
        "1|RIGHT FRONT SEAT": "restraint_info_10001_right_front_seat.json"
      },
      "intrusion_info": {
        "1": "intrusion_info_10001_empty.json"
      },
      "instrumentation_info": [
        "instrumentation_info_10001_page_0.json",
        "instrumentation_info_10001_page_1.json"
      ],
      "multimedia_files": "multimedia_files_10001.json",
      "vehicle_documents": "vehicle_documents_10001.json"
    }
  }
}
```

## `live_sample_manifest.csv`

```csv
test_no,reason
1,early legacy record; basic listing/detail shape
10,legacy VTB; metadata export contains TEST/VEHICLE/BARRIER/OCCUPANT
30,legacy NCAP VTB; zero injury metrics; report/video no photos
10001,modern frontal NCAP; 1 vehicle; barrier; 2 occupants; 634 instrumentation channels; many media/data packages
10003,modern side impact; 2 vehicles; impactor-as-vehicle; no barrier endpoint data; 63 instrumentation channels
10004,media-heavy modern test
10005,media-heavy modern test
```

## Fixture content 요구사항

### `metadata_10.json`

필수 section:

```text
TEST
VEHICLE
BARRIER
OCCUPANT
```

필수 field:

```text
TEST.TSTNO = 10
TEST.TSTDAT = legacy date string
TEST.TSTCFND = VEHICLE INTO BARRIER 또는 equivalent
VEHICLE.MAKED = PLYMOUTH
VEHICLE.MODELD = FURY
VEHICLE.YEAR = 1975
BARRIER.BARRIGD = DEFORMABLE 또는 RIGID 등 fixture 목적에 맞는 값
OCCUPANT.OCCLOC = LEFT FRONT SEAT / RIGHT FRONT SEAT
OCCUPANT.HIC = non-zero value
```

### `metadata_30.json`

zero/null/missing 구분용.

```text
OCCUPANT.HIC = 0 또는 "0"
OCCUPANT.LFEM = 0 또는 "0"
일부 optional metric = null
일부 field = missing
```

### `test_summary_10001.json`

필수 anomaly:

```text
testNo = 10001
testType = NEW CAR ASSESSMENT TEST
testDate = 2016-12-12
testConfiguration = VEHICLE INTO BARRIER
closingSpeed = 56.11
vehicleInformation = .../get-vehicle-info/10001
barrierInformation = .../get-vehicle-info/10001    # wrong link anomaly
instrumentationInformation = .../get-instrumentation-info/10001
documentInformation = .../vehicle-documents/test-no/10001
```

### `vehicle_info_10003.json`

```text
results length = 2
row 1: vehicleNo=1, vehicleMake=NHTSA, vehicleModel=DEFORMABLE IMPACTOR
row 2: vehicleNo=2, vehicleMake=CHEVROLET, vehicleModel=VOLT
```

### `barrier_info_10003_empty.json`

정상 status + empty results.

```json
{
  "meta": {"pagination": {"pageNumber": 0, "count": 0, "total": 0}, "status": 200, "message": "Success", "error": ""},
  "results": []
}
```

### `instrumentation_info_10001_page_*.json`

```text
page 0: pageNumber=0, count=20, total=634, nextUrl not null
page 1: pageNumber=1, total=634
```

테스트 목적상 실제 row는 40개만 저장해도 된다. 단, pagination/volume 테스트에서는 generator로 634개 canonical channel을 만들 수 있어야 한다.

### Media/documents

`multimedia_files_10001.json`은 photo/video/report를 포함한다. `vehicle_documents_10001.json`은 uds, abf, iso zip, tdms zip, other zip 또는 유사 data package URL을 포함한다. 실제 다운로드는 금지한다.

## Fixture client

생성/수정:

```text
src/nhtsa_metadata/sources/nhtsa_crash/fixtures.py
src/nhtsa_metadata/sources/nhtsa_crash/fixture_factory.py
```

동작:

```python
client.fetch(endpoint_name="test_summary", test_no=10001)
client.fetch(endpoint_name="instrumentation_info", test_no=10001, page_number=0)
client.fetch_all_pages(endpoint_name="instrumentation_info", test_no=10001)
```

요구사항:

- filesystem fixture 로드.
- missing fixture는 `FixtureNotFoundError`.
- 외부 HTTP 호출 금지.
- `fixture_manifest.json` 기반 endpoint/test_no/page mapping.
- generated fixture는 deterministic.

## Network guard

기본 tests에서 accidental network call이 발생하면 실패하게 한다.

예:

```python
@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("External network call is not allowed in default tests")
    monkeypatch.setattr(httpx.Client, "request", fail)
```

Live client test는 respx/fake transport만 사용한다.

## 테스트

```text
tests/test_fixtures.py
tests/test_fixture_client.py
```

검증:

- 모든 fixture JSON parse 가능.
- live_sample_manifest.csv column과 test_no 확인.
- 10001 summary fixture가 wrong barrierInformation link 포함.
- 10003 vehicle fixture가 2 rows 포함.
- 10003 barrier empty fixture가 failure로 간주되지 않음.
- 30 fixture가 zero/null/missing 포함.
- fixture client가 외부 HTTP 없이 payload 반환.
- instrumentation pagination fixture가 page/total 표현.

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
최소 fixture set 존재
fixture client가 endpoint matrix와 연결됨
basic tests에서 live API 호출 없음
10003 multi-vehicle fixture 재현
10001 instrumentation pagination fixture 재현
```


---

# Phase 4 — Parser / Normalizer 작업지시서

## 목표

NHTSA source payload를 endpoint별 Source DTO로 파싱하고 canonical DB row spec으로 매핑한다. 이 phase는 DB write를 최소화하거나 in-memory DTO 중심으로 테스트해도 된다. Full ingestion/upsert는 Phase 5에서 구현한다.

## 처리 계층

```text
raw payload
  -> endpoint source parser
  -> source DTO
  -> canonical mapper
  -> canonical row specs
  -> field catalog observations
  -> section observations
```

## 생성/수정 파일

```text
src/nhtsa_metadata/sources/nhtsa_crash/parsers.py
src/nhtsa_metadata/sources/nhtsa_crash/dtos.py
src/nhtsa_metadata/sources/nhtsa_crash/field_aliases.py
src/nhtsa_metadata/sources/nhtsa_crash/field_catalog.py
src/nhtsa_metadata/sources/nhtsa_crash/normalization.py
src/nhtsa_metadata/services/canonical_mapper.py
src/nhtsa_metadata/services/read_model_builder.py
tests/test_parsers_metadata.py
tests/test_parsers_api_detail.py
tests/test_field_catalog.py
tests/test_normalization.py
tests/test_canonical_mapper.py
docs/phase_reports/2026-04-28__bootstrap-phase-4__pass__phase-4-report.md
```

## DTO 설계

Source-level DTO:

```python
class SourceRow:
    endpoint_name: str
    section_name: str | None
    json_path: str
    row_hash: str
    data: dict[str, Any]

class ParsedSourcePayload:
    endpoint_name: str
    test_no: int | None
    source_rows: list[SourceRow]
    sections: list[SectionObservation]
    field_observations: list[FieldObservation]
```

Canonical row specs:

```text
CanonicalTestSpec
CanonicalVehicleSpec
CanonicalBarrierSpec
CanonicalParticipantSpec
CanonicalOccupantSpec
CanonicalRestraintSpec
CanonicalInstrumentationChannelSpec
CanonicalInstrumentationDetailSpec
CanonicalInjuryMetricSpec
CanonicalDeformationMeasurementSpec
CanonicalIntrusionMeasurementSpec
CanonicalMediaAssetSpec
```

모든 spec는 lineage fields를 포함한다.

## Normalization utilities

### Date parsing

```python
def parse_legacy_date(raw: object) -> ParsedDate: ...
```

반환:

```text
raw
date
year
month
day
status = parsed | partial | invalid | missing | empty
```

규칙:

```text
None -> missing
"" -> empty
YYYY-MM-DD valid -> parsed
YYYY-00-DD 또는 YYYY-MM-00 -> partial, date None, 가능한 year/month/day 저장
형식 불일치 -> invalid + raw 보존
```

### Number parsing

```python
def parse_number(raw: object, field_present: bool = True) -> ParsedNumber: ...
```

반환:

```text
raw
value: Decimal | None
status = parsed | null | missing | empty | invalid
```

규칙:

```text
field_present false -> missing
None -> null
"" -> empty
"0" 또는 0 -> parsed Decimal("0")
"56.11" -> parsed Decimal("56.11")
"N/A" -> invalid
```

### Hashing

```python
def canonical_json_hash(value: object) -> str: ...
```

- `json.dumps(..., sort_keys=True, separators=(",", ":"))`
- Decimal/date는 string serialization.
- key order와 무관하게 stable hash.

## Parser 요구사항

### API wrapper

모든 API-style payload에서 추출:

```text
meta.pagination
meta.status
meta.message
meta.error
results[]
```

### Section detector

Metadata export section:

```text
TEST
VEHICLE
BARRIER
OCCUPANT
RESTRAINT
INSTRUMENTATION
URL
REPORTS
VIDEOS
PHOTOS
```

API detail endpoint section:

```text
test_summary
vehicle_info
barrier_info
occupant_info
restraint_info
intrusion_info
instrumentation_info
multimedia_files
vehicle_documents
```

### Field catalog walker

재귀적으로 field path 수집.

예:

```text
$.results[*].vehicleMake
$.results[0].vehicleMake
$.results[0].TEST[0].TSTNO
```

FieldObservation:

```text
endpoint_name
section_name
field_path
observed_type
is_non_null
example_value
mapping_status
mapped_table
mapped_column
```

### Unknown field policy

- Alias map에 있으면 `mapped`.
- 의미는 알지만 canonical column이 없으면 `mapped_to_extra_json`.
- 그 외 `unmapped`.
- 어떤 경우에도 raw row data 폐기 금지.

## Canonical mapper 요구사항

### Tests

입력:

```text
test_summary
metadata_export.TEST
test_detail optional
```

우선순위:

```text
1. test_summary API detail
2. metadata_export TEST
3. test_detail optional
```

충돌 후보는 conflict observation으로 반환한다. DB 저장은 Phase 5.

### Vehicles

입력:

```text
vehicle_info
metadata_export.VEHICLE
vehicle_detail optional
```

Natural key: `test_no + source_vehicle_no`.

`source_vehicle_no`가 없으면 row order 기반 임시 번호를 쓰고 `extra_json`에 기록한다.

### Test participants

차량 row:

```text
vehicleMake == 'NHTSA' and vehicleModel contains 'IMPACTOR' -> impactor_vehicle
else -> subject_vehicle
```

Barrier row:

```text
barrier row exists -> participant_kind=barrier
```

### Barriers

입력:

```text
barrier_info
metadata_export.BARRIER
```

Empty endpoint는 canonical barrier row 0개 허용. source section은 기록한다.

### Occupants

입력:

```text
occupant_info
metadata_export.OCCUPANT
occupant_detail optional
```

Link key: `test_no + source_vehicle_no + occupant_location_raw`.

### Injury metrics

OCCUPANT row에서 long-form 생성.

최소 metric:

```text
HIC
CSI
TTI
PELVG
LFEM
RFEM
LBELT
SBELT
T1
T2
```

규칙:

- missing field는 row 생성 안 함.
- null은 기본적으로 row 생성 안 함. 필요시 parse_status null row 허용 가능.
- `0` 또는 `'0'`은 반드시 row 생성, numeric_value=0.
- raw field path lineage 보존.

### Deformation measurements

VEHICLE row에서 long-form 생성.

```text
DPD1..DPD6
AX1..AXn
BX1..BXn
DAMDST
CRHDST
PDOF
VDI
```

`VDI` 같은 코드성 값은 raw_value만 보존하고 numeric_value null.

### Restraints

입력:

```text
restraint_info
metadata_export.RESTRAINT
```

특수 key:

```text
inflationer/BeltPretensionerDeployment
```

DB column명으로 직접 쓰지 말고 `deployment_status` 또는 `pretensioner_deployment`로 매핑한다. 원본 key는 raw_row_json과 field_catalog에 남긴다.

### Instrumentation channels

입력:

```text
instrumentation_info
metadata_export.INSTRUMENTATION
```

Natural key: `test_no + curve_no`.

Mapping 후보:

```text
curveNo
sensorType
sensorLocation
sensorAttachment
axisDirofSensor
unit
firstPoint
lastPoint
timeIncrement
channelStatus
dataStatus
commentary
```

### Intrusion measurements

Empty endpoint는 canonical intrusion row 0개 허용.

### Media assets

입력:

```text
multimedia_files
vehicle_documents
metadata_export.URL/REPORTS/VIDEOS/PHOTOS
```

asset kind inference:

```text
.jpg/.jpeg/.png -> photo
.mp4/.mov/.wmv/.avi -> video
.pdf -> report 또는 document
url/filename contains uds -> uds 또는 data_package
contains tdms -> tdms 또는 data_package
contains abf -> abf 또는 data_package
contains iso -> iso 또는 data_package
.zip -> zip 또는 data_package
else -> other
```

다운로드 금지.

## 테스트

```text
tests/test_normalization.py
tests/test_parsers_metadata.py
tests/test_parsers_api_detail.py
tests/test_canonical_mapper.py
```

필수 검증:

- valid/partial/invalid date parse.
- number parse: `0`, `'0'`, `None`, missing sentinel, empty string, nonnumeric.
- hash stable across key order.
- `metadata_10.json` section 인식.
- `metadata_30.json` zero metrics value 인식.
- unknown fields field_observations에 포함.
- 10001 summary wrong link는 parse되지만 endpoint authority로 사용하지 않음.
- 10003 vehicle rows -> 2 vehicles.
- 10003 barrier empty -> section row_count=0.
- 10001 instrumentation pagination capture.
- 10003 participant kind includes `impactor_vehicle`.
- media_assets include data package kind.
- every canonical spec has lineage fields.

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
parser가 source_rows/sections/field_observations 반환
canonical mapper가 domain별 row specs 반환
zero/null/missing 구분 테스트 통과
10003 impactor-as-vehicle 분류 테스트 통과
unknown field 보존
```


---

# Phase 5 — Ingestion / Rebuild 작업지시서

## 목표

Fixture/source client payload를 DB에 저장하고, parser/mapper 결과를 canonical tables에 idempotent하게 upsert한다. 또한 raw payload에서 canonical/read-model을 재생성하는 rebuild flow를 구현한다.

## 범위

구현 대상:

```text
source payload 저장
source payload observation 저장
source section 저장
field catalog upsert
canonical row upsert
canonical_row_sources 저장
source_conflicts 저장
read model rebuild
catalog CLI 확장
coverage report CLI
fixture client 기반 collect-test/collect/rebuild 테스트
```

Live HTTP client는 safety skeleton 또는 fake transport까지만 구현한다. 실제 manual live command 완성은 Phase 7.

## 생성/수정 파일

```text
src/nhtsa_metadata/services/source_payload_service.py
src/nhtsa_metadata/services/field_catalog_service.py
src/nhtsa_metadata/services/ingestion_service.py
src/nhtsa_metadata/services/canonical_upsert.py
src/nhtsa_metadata/services/conflict_service.py
src/nhtsa_metadata/services/read_model_builder.py
src/nhtsa_metadata/services/coverage_service.py
src/nhtsa_metadata/services/catalog_builder.py
src/nhtsa_metadata/cli.py

tests/test_source_payload_service.py
tests/test_field_catalog_service.py
tests/test_ingestion_idempotency.py
tests/test_catalog_builder_fixture.py
tests/test_rebuild.py
tests/test_coverage_report.py

docs/phase_reports/2026-04-28__bootstrap-phase-5__pass__phase-5-report.md
```

## SourcePayloadService

```python
class SourcePayloadService:
    def save_payload(self, fetch_result: SourceFetchResult, run_id: int | None, run_item_id: int | None) -> SourcePayload:
        ...

    def save_sections(self, source_payload_id: int, sections: list[SectionObservation]) -> None:
        ...

    def get_latest_payloads_for_test(self, test_no: int, endpoint_names: list[str] | None = None) -> list[SourcePayload]:
        ...
```

규칙:

- `canonical_url_hash`는 normalized request URL에서 계산.
- `payload_hash`는 full JSON payload에서 계산.
- `source_payloads`는 `(endpoint_name, canonical_url_hash, payload_hash)`로 upsert.
- fetch 이벤트마다 `source_payload_observations`는 항상 insert.
- pagination fields 저장.
- empty endpoint도 정상 payload로 저장.

## FieldCatalogService

```python
class FieldCatalogService:
    def record_observations(self, observations: Iterable[FieldObservation]) -> None:
        ...

    def snapshot(self, run_id: int | None = None) -> FieldCoverageSnapshot:
        ...
```

규칙:

- unique key: `endpoint_name + section_name + field_path`
- `seen_count` 증가.
- non-null이면 `non_null_count` 증가.
- `first_seen_at` 보존.
- `last_seen_at` 갱신.
- example values는 최대 5개 저장.

## Canonical upsert

구현 함수:

```python
upsert_test(spec)
upsert_vehicle(test_id, spec)
upsert_barrier(test_id, spec)
upsert_participant(test_id, spec)
upsert_occupant(test_id, vehicle_id, spec)
upsert_restraint(test_id, vehicle_id, occupant_id, spec)
upsert_instrumentation_channel(test_id, vehicle_id, occupant_id, spec)
upsert_injury_metric(test_id, vehicle_id, occupant_id, spec)
upsert_deformation_measurement(test_id, vehicle_id, spec)
upsert_intrusion_measurement(test_id, vehicle_id, spec)
upsert_media_asset(test_id, spec)
upsert_code_value(code_set, code_value, ...)
```

규칙:

- Phase 2 natural keys 사용.
- 같은 natural key + 같은 source hash는 중복 생성 금지.
- 같은 natural key + source hash 변경 시 update.
- upsert 후 `canonical_row_sources` association 작성.
- `raw_row_json`, `extra_json`, lineage 보존.

## ConflictService

Semantic conflict 최소 키:

```text
tests.test_date_raw
tests.closing_speed
tests.test_configuration
vehicles.make
vehicles.model
vehicles.model_year
barriers.rigidity
barriers.shape
```

규칙:

- 서로 다른 endpoint가 같은 semantic key에 대해 다른 non-empty 값을 주면 unresolved conflict 저장.
- 기본적으로 실패시키지 않는다.
- `--stop-on-source-conflict`가 있으면 current item abort.

## ReadModelBuilder

```python
class ReadModelBuilder:
    def rebuild_test(self, test_id: int) -> None:
        ...

    def rebuild_all(self) -> None:
        ...
```

Build:

```text
test_filter_summary
test_facets
asset_summary
```

Facet emission:

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

Range bucket v1 예:

```text
closing_speed: 0-10, 10-25, 25-40, 40-55, 55-70, 70+, unknown
injury_metric_range: exact numeric은 canonical에서, bucket facet은 optional
```

## CatalogBuilder

```python
class CatalogBuilder:
    def discover(...): ...
    def collect_test(test_no: int, endpoint_set: str, paginate_instrumentation: bool, source: str) -> CollectResult: ...
    def collect_manifest(manifest_path: Path, ...) -> CollectManifestResult: ...
    def rebuild_test(test_no: int, rebuild_read_models: bool = True) -> RebuildResult: ...
```

Endpoint collection order:

```text
1. test_summary
2. metadata_export
3. test_detail optional
4. vehicle_info
5. vehicle_detail per vehicle optional
6. barrier_info
7. occupant_info
8. occupant_detail per occupant optional
9. restraint_info per occupant
10. intrusion_info per vehicle
11. instrumentation_info all pages
12. instrumentation_detail optional/per curve when explicitly requested
13. multimedia_files
14. vehicle_documents
```

기본 v1에서는 instrumentation detail for every curve를 자동 호출하지 않는다.

## CLI

필수 commands:

```powershell
python -m nhtsa_metadata.cli catalog discover --max-pages 1 --source fixture
python -m nhtsa_metadata.cli catalog collect-test --test-no 10001 --source fixture --endpoint-set all --paginate-instrumentation
python -m nhtsa_metadata.cli catalog collect --manifest tests/fixtures/live_sample_manifest.csv --source fixture
python -m nhtsa_metadata.cli catalog rebuild --test-no 10001 --database-url sqlite:///data/nhtsa_metadata.sqlite
python -m nhtsa_metadata.cli coverage report --database-url sqlite:///data/nhtsa_metadata.sqlite
```

필수 options:

```text
--dry-run
--database-url
--source fixture|live
--allow-live
--endpoint-set summary|metadata|detail|assets|all
--paginate-instrumentation / --no-paginate-instrumentation
--save-fixture
--stop-on-source-conflict
--allow-empty-endpoints / --no-allow-empty-endpoints
--retry-count
--timeout-seconds
--rate-limit-delay-seconds
--resume
--max-pages
--max-items
```

Live safety:

```text
source == live and allow_live == false -> UsageError
source == live and settings.allow_live == false and env not set -> UsageError
source == fixture -> no network
```

## Dry-run

`--dry-run`:

- manifest/test list resolve.
- endpoint matrix resolve.
- planned operations print.
- DB insert 없음.
- 권장: collection_runs도 생성하지 않음.

## Resume

`--resume`:

- 동일 manifest hash/endpoint_set의 incomplete run 탐색.
- succeeded item skip.
- failed/partial/pending retry.
- v1은 단순 구현 허용: 같은 DB에서 이미 succeeded인 test_no skip.
- limitation은 문서화.

## Rebuild

`catalog rebuild --test-no 10001`:

1. source_payloads load.
2. 해당 test canonical rows dependency order로 삭제.
3. stored payload parser/mapper 재실행.
4. canonical upsert.
5. read model rebuild.
6. counts 출력.

주의:

- source_payloads 삭제 금지.
- rebuild도 collection_runs에 기록 가능.

## 테스트

### Source payload

- save once -> source_payloads 1, observations 1.
- same payload again -> source_payloads 1, observations 2.
- changed payload -> source_payloads 2.
- empty results 저장.

### Idempotency

- 10001 fixture ingest.
- table counts 기록.
- 동일 fixture ingest 재실행.
- canonical/read-model counts 불변. run/observation counts 증가는 허용.

### Catalog builder

- collect-test 10001 -> test/vehicle/barrier/occupant/restraint/instrumentation/media rows.
- collect-test 10003 -> 2 vehicles + impactor participant.
- empty barrier endpoint failure 아님.
- dry-run no rows.

### Rebuild

- collect 10001.
- canonical/read-model counts capture.
- 일부 canonical row 삭제.
- rebuild from source_payloads.
- counts restored.

### Coverage report

- mapped/unmapped fields 존재.
- CLI report 성공.

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
fixture collect-test works for 10001 and 10003
same fixture re-collection does not duplicate canonical rows
raw source_payloads remain available
rebuild from raw source_payloads works
field coverage report works
live source cannot run without --source live --allow-live
```


---

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

docs/phase_reports/2026-04-28__bootstrap-phase-6__pass__phase-6-report.md
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


---

# Phase 7 — Manual Live Validation 작업지시서

## 목표

기본 verify/harness와 완전히 분리된 수동 live validation을 구현한다. 목적은 실제 NHTSA API shape가 fixture/mock와 크게 다르지 않은지 확인하고, baseline test_no에 대해 row count와 anomaly handling을 검증하는 것이다.

## 절대 원칙

```text
기본 pytest/verify/harness에서는 live 호출 금지
live 호출은 --source live + --allow-live가 모두 있을 때만 허용
실제 파일 다운로드 금지
manual live validation 결과는 phase report에 기록
```

## 생성/수정 파일

```text
src/nhtsa_metadata/sources/nhtsa_crash/live_client.py
src/nhtsa_metadata/services/live_baseline_assertions.py
src/nhtsa_metadata/cli.py
scripts/live_validate.ps1

tests/test_live_client_safety.py
tests/test_live_baseline_assertions_fixture.py

docs/phase_reports/2026-04-28__bootstrap-phase-7__pass__phase-7-report.md
```

## Live client

```python
class LiveNhtsaClient:
    def __init__(
        self,
        settings: Settings,
        allow_live: bool,
        timeout_seconds: float,
        retry_count: int,
        rate_limit_delay_seconds: float,
    ): ...

    def fetch(self, endpoint_name: str, **path_and_query: object) -> SourceFetchResult: ...

    def fetch_all_pages(self, endpoint_name: str, **path_and_query: object) -> list[SourceFetchResult]: ...
```

Safety:

```python
if not allow_live or not settings.allow_live:
    raise LiveAccessNotAllowedError
```

Enablement:

- CLI option `--allow-live` sets command-level allow flag.
- 환경변수 `NHTSA_METADATA_ALLOW_LIVE=1` 또는 settings `allow_live=true`.
- command-level과 settings/env-level 모두 허용되어야 live 실행 가능.

Retry:

```text
Retry: 429, 500, 502, 503, 504
No retry: 400, 404 by default
Backoff: exponential 또는 fixed delay
Respect --rate-limit-delay-seconds
```

Pagination:

- instrumentation endpoint는 pageNumber 0부터 반복.
- `nextUrl`이 있거나 accumulated count < total_available이면 계속.
- repeated URL/page guard로 infinite loop 방지.

URL rendering:

- `endpoints.py` template 사용.
- summary link를 required endpoint authority로 사용하지 않음.
- occupantLocation path parameter percent-encode.

## CLI live commands

Collect live manifest:

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog collect `
  --manifest tests\fixtures\live_sample_manifest.csv `
  --database-url sqlite:///data/live_validation.sqlite `
  --source live `
  --allow-live `
  --endpoint-set all `
  --paginate-instrumentation `
  --retry-count 2 `
  --timeout-seconds 30 `
  --rate-limit-delay-seconds 0.2
```

Coverage:

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli coverage report `
  --database-url sqlite:///data/live_validation.sqlite
```

Baseline:

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog assert-live-baseline `
  --database-url sqlite:///data/live_validation.sqlite
```

Convenience script:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\live_validate.ps1 -AllowLive
```

`scripts/live_validate.ps1`는 `-AllowLive` parameter가 없으면 실패해야 한다. 이 script는 `scripts/verify.ps1`에서 호출하지 않는다.

## Baseline assertions

### 10001

```text
tests = 1
vehicles >= 1
barriers >= 1
occupants >= 2
restraints >= 6
instrumentation_channels >= 634
intrusion source payload exists
canonical intrusion rows may be 0
media_assets include at least one of photo/video/report/data_package
vehicle_documents source payload exists
```

### 10003

```text
tests = 1
vehicles >= 2
participants include impactor_vehicle
barrier endpoint source payload exists; canonical barriers may be 0
occupants >= 2
instrumentation_channels >= 63
media_assets include photos and report if present from source
```

### General

```text
source_payloads exist for attempted required endpoints unless run item records failure
collection_run status is succeeded or partial, not silently missing
field_catalog has rows
field_coverage_snapshot exists
```

## Phase report

`docs/phase_reports/2026-04-28__bootstrap-phase-7__pass__phase-7-report.md`:

```markdown
# Phase 7 Manual Live Validation Report

## Run Metadata
- date/time:
- database_url:
- manifest:
- endpoint_set:
- paginate_instrumentation:
- retry_count:
- timeout_seconds:

## Baseline Results
| test_no | assertion | expected | actual | result |
|---:|---|---:|---:|---|
| 10001 | instrumentation_channels | >=634 | ... | pass/fail |
| 10003 | vehicles | >=2 | ... | pass/fail |

## Source Payload Counts
| test_no | endpoint | payload pages | result count | status |
|---:|---|---:|---:|---|

## Field Coverage
- total fields:
- mapped:
- mapped_to_extra_json:
- unmapped:
- conflicts:

## Anomalies Observed
- wrong summary links:
- empty endpoints:
- invalid dates:
- pagination issues:

## Verification
- live collect: pass/fail
- coverage report: pass/fail
- baseline assertion: pass/fail

## Follow-up Work
- ...
```

Do not claim live success unless the manual command was actually run.

## Tests

`tests/test_live_client_safety.py`:

- live client with allow_live false raises.
- `--source live` without `--allow-live` fails before HTTP.
- `--allow-live` without settings/env allow fails.
- fixture source still works.
- Use fake transport/respx only.

`tests/test_live_baseline_assertions_fixture.py`:

- baseline assertions pass against fixture DB simulating 10001/10003 counts.
- missing instrumentation count fails with actionable message.
- empty intrusion/barrier canonical rows do not fail when source payload exists.

## 완료 기준

Default verification still passes and makes no live call:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check src tests
.venv\Scripts\python.exe -m mypy src\nhtsa_metadata
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
powershell -ExecutionPolicy Bypass -File .harness\run.ps1
```

Manual live validation command exists:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\live_validate.ps1 -AllowLive
```

Completion requires either actual live phase report results or an explicit statement that live execution was not performed due to network/access limits while safety and fixture baseline tests passed.


---

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


---

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


---

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

- [ ] `2026-05-02__classifier-v1-4-failure-package__recorded__v1-4-full-corpus-failure-package.md` defines metadata-only scope.
- [ ] `AGENTS.md` contains guardrails.
- [ ] `docs/2026-04-28__source-contract__current__source-contract.md` exists.
- [ ] `docs/2026-04-28__source-contract__current__source-endpoint-matrix.md` includes `get-test-detail/{testNo}` optional endpoint.
- [ ] `docs/2026-04-28__source-contract__current__source-field-aliases.md` exists.
- [ ] `docs/2026-04-28__source-contract__current__source-anomalies.md` documents wrong summary link, pagination, empty endpoint, multi-vehicle, date anomalies, zero/null.
- [ ] `docs/2026-04-28__contract__current__db-schema-contract.md` exists.
- [ ] `docs/2026-04-28__schema__current__db-schema.md` matches implemented schema.
- [ ] `docs/2026-04-28__contract__current__catalog-builder-contract.md` exists.
- [ ] `docs/2026-04-28__contract__current__filtering-contract.md` exists.
- [ ] `docs/2026-04-28__contract__current__field-coverage-contract.md` exists.
- [ ] `docs/2026-04-28__operations__current__operations.md` exists.
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
- [ ] `docs/2026-04-28__migration-notes__current__postgresql-migration-notes.md` exists.
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


---

