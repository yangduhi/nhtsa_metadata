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
docs/phase_reports/phase_4_parser_normalizer.md
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
