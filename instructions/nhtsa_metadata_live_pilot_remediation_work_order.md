# nhtsa_metadata 후속 작업지시서: Live Pilot 부분 통과 Remediation

## 0. 판정

현재 25건 bounded live pilot은 **부분 통과**로 판정한다.

통과한 항목:

- live manifest 생성
- bounded collect
- schema audit
- scale report
- API smoke
- baseline 10001/10003 주요 조건
- live safety negative
- Git clean 조건

미통과 또는 조사 필요 항목:

- `restraints` canonical duplicate group = 42
- 10001/10003 `media_assets`에서 `data_package` asset kind = 0
- 10001/10003 occupant canonical count가 각각 4로 관측되어, baseline 의미상 expected semantic occupant cardinality와 현 canonical identity가 일치하는지 점검 필요
- `restraint_info` payload coverage가 25건 pilot 전체에서 2건에 그쳐 endpoint matrix scheduling 범위 확인 필요

## 1. 금지 사항

다음은 수행하지 않는다.

- full crawler 구현 금지
- 100~250건 bounded pilot 확장 금지
- 전체 NHTSA range scan 금지
- 파일 다운로드 금지
- waveform/TDMS/UDS/ABF/ISO zip 내용 분석 금지
- 기본 verify/harness에 live API 호출 추가 금지
- `data/*.sqlite`, live manifest, audit report 등 산출물 commit 금지

## 2. 목표

이번 remediation의 목표는 다음 5가지다.

1. `restraints` canonical duplicate group을 0으로 만든다.
2. duplicate source observation은 canonical row를 새로 만들지 않고 기존 canonical row에 `canonical_row_sources`로 연결한다.
3. schema audit의 공식 duplicate coverage에 `occupants`, `restraints`, `instrumentation_channels`, `media_assets`를 포함한다.
4. `vehicle_documents` / `multimedia_files` asset parser를 점검하여 `data_package`가 source absence인지 parser classification 누락인지 판정한다.
5. 동일 25건 pilot 또는 기존 raw payload rebuild 기준으로 remediation 결과를 검증한 뒤에만 100건 bounded pilot 확장을 허용한다.

## 3. Step 1 — 현재 상태 재확인

```powershell
git status
git rev-parse --short HEAD
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check src tests
.venv\Scripts\python.exe -m mypy src\nhtsa_metadata
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
powershell -ExecutionPolicy Bypass -File .harness\run.ps1
```

성공 기준:

```text
working tree clean
HEAD = 4fe0a5a 또는 그 이후 main commit
pytest 통과
ruff 통과
mypy 통과
verify 통과
harness 통과
```

## 4. Step 2 — duplicate 원인 추적 기능 추가

`schema audit`에 duplicate detail 출력 옵션을 추가한다.

예상 명령:

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli schema audit `
  --database-url sqlite:///data/stratified_live_pilot.sqlite `
  --output data/schema_audit_report.json `
  --include-duplicate-details `
  --duplicate-detail-limit 50
```

출력 JSON에 다음 구조를 추가한다.

```json
{
  "canonical_duplicate_groups": {
    "vehicles": {"group_count": 0, "row_count": 0},
    "test_participants": {"group_count": 0, "row_count": 0},
    "barriers": {"group_count": 0, "row_count": 0},
    "occupants": {"group_count": 0, "row_count": 0},
    "restraints": {"group_count": 42, "row_count": 0},
    "instrumentation_channels": {"group_count": 0, "row_count": 0},
    "media_assets": {"group_count": 0, "row_count": 0}
  },
  "duplicate_details": {
    "restraints": [
      {
        "semantic_key": "...",
        "test_no": 10001,
        "vehicle_no": 1,
        "occupant_location_key": "LEFT FRONT SEAT",
        "restraint_type": "FRONTAL AIRBAG",
        "row_ids": [1, 2],
        "source_payload_ids": [10, 11],
        "source_endpoint_names": ["metadata_export", "test_detail"]
      }
    ]
  }
}
```

Duplicate detail은 raw payload 전문을 출력하지 않는다. 필요한 식별자, semantic key, source endpoint, row id만 출력한다.

## 5. Step 3 — `restraints` semantic identity 정의

`restraints` canonical row는 source row hash가 아니라 **의미 기반 semantic key**로 upsert한다.

권장 semantic components:

```text
test_id
vehicle_scope_key
occupant_scope_key
restraint_type_key
restraint_location_key
deployment_status_key
mount_or_system_key
```

정규화 규칙:

```text
- trim
- upper-case
- repeated whitespace collapse
- empty string -> NULL_SENTINEL
- unknown/null/missing은 서로 구분 가능하게 보존하되, unique key에는 stable sentinel 사용
- raw source row hash는 lineage용이며 canonical identity에는 사용하지 않음
```

권장 구현:

```text
restraints.semantic_key TEXT NOT NULL
restraints.semantic_hash TEXT NOT NULL
UNIQUE(test_id, semantic_hash)
```

SQLite에서 nullable unique column이 중복 허용되는 문제를 피하기 위해 semantic key에 sentinel을 포함하고, unique index는 nullable column 조합이 아니라 `semantic_hash` 기반으로 둔다.

## 6. Step 4 — canonical upsert / merge policy 수정

`canonical_upsert.py`에서 restraints 처리 정책을 다음처럼 바꾼다.

```text
1. semantic_hash 계산
2. 동일 test_id + semantic_hash existing row 조회
3. existing row가 있으면 새 canonical row 생성 금지
4. existing row에 canonical_row_sources 추가
5. canonical column은 endpoint priority와 non-null merge 정책으로 보강
6. 값 충돌이 있으면 source_conflicts에 기록
```

Endpoint priority 권장값:

```text
restraint_info
occupant_detail
occupant_info
test_detail
metadata_export
```

Merge policy:

```text
- existing value가 null이고 incoming value가 non-null이면 채움
- existing value와 incoming value가 동일하면 유지
- existing value와 incoming value가 다르면 source_conflicts 기록
- source priority가 높은 endpoint의 값은 canonical display value로 승격 가능
- raw_row_json은 primary source row만 보관하되 모든 source row는 canonical_row_sources로 추적
```

## 7. Step 5 — `canonical_row_sources` 중복 연결 방지

동일 canonical row와 동일 source payload row가 여러 번 연결되지 않도록 natural key를 둔다.

권장 unique key:

```text
UNIQUE(canonical_table, canonical_id, source_payload_id, source_row_path, source_row_hash)
```

이미 동일 연결이 있으면 insert하지 않는다.

## 8. Step 6 — `restraint_info` endpoint scheduling 점검

현재 pilot report에서 `restraint_info` payloads가 2건으로 관측되었다. 이는 25건 pilot 전체 대비 낮다. endpoint matrix scheduling이 다음처럼 동작하는지 확인한다.

```text
1. test_no별 occupant_info 수집
2. occupant row에서 vehicle_no, occupant_location 추출
3. occupant_location을 API path segment로 URL encode
4. get-restraint-info/{vehicleNo}/{testNo}/{occupantLocation} 호출
5. empty response도 source_payload로 저장
6. 호출 scope를 source_payloads에 보존
```

필수 테스트:

```text
- occupant 2명 fixture/mock -> restraint_info endpoint 2회 scheduling
- occupant_location이 공백 포함 문자열인 경우 URL encoded path 사용
- empty API response라도 source_payloads에 저장
- source link 문자열은 endpoint authority로 사용하지 않음
```

## 9. Step 7 — baseline semantic cardinality audit 추가

10001/10003은 baseline fixture/live sanity anchor로 쓰인다. 현재 pilot에서 occupants가 각각 4로 관측되었으므로, 기존 duplicate audit만으로는 semantic duplication을 놓칠 수 있다.

`schema audit`에 다음 optional baseline audit을 추가한다.

```json
{
  "baseline_semantic_cardinality": {
    "10001": {
      "occupants_expected_min": 2,
      "occupants_expected_exact_when_normalized": 2,
      "occupants_actual": 4,
      "status": "investigate"
    },
    "10003": {
      "vehicles_expected_min": 2,
      "instrumentation_expected_min": 63,
      "status": "pass"
    }
  }
}
```

단, 이 audit은 처음에는 warning으로 둔다. `restraints` duplicate fix와 동시에 occupant semantic identity도 필요한지 판단한다.

## 10. Step 8 — media/data package classification audit

`vehicle_documents` payload가 25건 존재하는데 `data_package` asset kind가 0으로 관측되었다. parser 누락인지 source absence인지 판정한다.

추가 audit 항목:

```json
{
  "asset_classification_audit": {
    "vehicle_documents_payloads": 25,
    "multimedia_files_payloads": 25,
    "document_rows_observed": 0,
    "data_package_candidates": 0,
    "classified_data_packages": 0,
    "unclassified_asset_candidates": []
  }
}
```

`media_assets` 권장 taxonomy:

```text
photo
video
report
data_package
document
other
```

`asset_subtype` 권장값:

```text
UDS
EV
ABF
ISO
TDMS
ZIP
PDF
HTML
UNKNOWN
```

Classification rule 예시:

```text
- photo/video/report는 multimedia_files source type을 우선 사용
- vehicle_documents 중 PDF/report 성격은 report 또는 document
- UDS/EV/ABF/ISO/TDMS/zip data bundle은 data_package
- 확신 불가하면 other로 저장하고 unclassified_asset_candidates에 남김
```

Read model/facet:

```text
asset_kind
data_package subtype
has_uds_or_tdms_package
```

## 11. Step 9 — fixture 추가

다음 fixture 또는 mock case를 추가한다.

```text
tests/fixtures/nhtsa/restraint_duplicate_case_10001.json
tests/fixtures/nhtsa/media_document_data_package_case_10001.json
```

실제 live DB를 commit하지 않는다. 필요한 최소 source payload JSON만 fixture로 저장한다.

필수 테스트:

```text
- 동일 semantic restraint가 metadata_export/test_detail/restraint_info에서 들어와도 canonical restraints row는 1개
- source observation은 canonical_row_sources 여러 개로 연결
- conflict 발생 시 source_conflicts 기록
- 동일 fixture 재처리 시 restraints row count 증가 없음
- media document data package 후보가 data_package로 분류됨
- has_uds_or_tdms_package facet 생성
```

## 12. Step 10 — 기존 25건 DB rebuild 검증

가능하면 live API 재호출 전에 기존 raw payload만으로 rebuild한다.

예상 명령:

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog rebuild `
  --database-url sqlite:///data/stratified_live_pilot.sqlite

.venv\Scripts\python.exe -m nhtsa_metadata.cli schema audit `
  --database-url sqlite:///data/stratified_live_pilot.sqlite `
  --output data/schema_audit_report_after_restraint_fix.json `
  --include-duplicate-details
```

성공 기준:

```text
restraints duplicate groups = 0
vehicles duplicate groups = 0
test_participants duplicate groups = 0
barriers duplicate groups = 0
occupants duplicate groups = 0 또는 known warning으로 명시
instrumentation_channels duplicate groups = 0
media_assets duplicate groups = 0
canonical_row_sources 증가 가능
canonical restraints row count는 중복 제거 방향으로 감소
source_payloads/source_payload_observations는 보존
```

## 13. Step 11 — 동일 25건 live pilot 재실행

endpoint scheduling 또는 live asset classification 확인이 필요하면 동일 범위에서만 재실행한다.

```powershell
$env:NHTSA_METADATA_ALLOW_LIVE="true"

powershell -ExecutionPolicy Bypass -File scripts\live_pilot_validate.ps1 `
  -AllowLive `
  -DatabaseUrl sqlite:///data/stratified_live_pilot_after_fix.sqlite `
  -Manifest data/stratified_live_pilot_manifest.csv
```

성공 기준:

```text
script exit code 0
manifest row count = 25
10001 포함
10003 포함
full crawler 미실행
파일 다운로드 미실행
restraints duplicate groups = 0
schema audit 공식 duplicate coverage 전체 table pass
safety negative test 유지
```

## 14. Step 12 — 기본 검증

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check src tests
.venv\Scripts\python.exe -m mypy src\nhtsa_metadata
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
powershell -ExecutionPolicy Bypass -File .harness\run.ps1
```

성공 기준:

```text
pytest 통과
ruff 통과
mypy 통과
verify 통과
harness 통과
기본 검증에 live call 없음
```

## 15. 최종 보고 형식

```text
결론:
- remediation 통과 / 부분 통과 / 실패

변경 내용:
- restraint semantic key
- canonical upsert merge policy
- canonical_row_sources idempotency
- schema audit duplicate coverage 확장
- media/data_package classification audit
- restraint_info endpoint scheduling 변경 여부

검증:
- pytest/ruff/mypy/verify/harness
- existing 25건 DB rebuild 결과
- 동일 25건 live pilot 재실행 여부
- safety negative 결과

핵심 수치:
- tests
- source_payloads
- source_payload_observations
- canonical restraints row count
- restraints duplicate groups
- occupants duplicate groups
- instrumentation_channels duplicate groups
- media_assets duplicate groups
- data_package asset count
- unmapped field count

Baseline:
- 10001 vehicles/barriers/occupants/restraints/instrumentation/media
- 10003 vehicles/participants/occupants/restraints/instrumentation/media

판정:
- 100건 bounded pilot 확장 가능 여부
- 확장 불가 시 blocking issue

Git:
- branch
- commit
- status
- push 여부
```

## 16. 100건 bounded pilot 확장 조건

다음 조건을 모두 만족해야 100건 bounded pilot로 확장한다.

```text
1. 25건 live pilot 또는 25건 raw rebuild에서 restraints duplicate groups = 0
2. schema audit 공식 duplicate coverage가 occupants/restraints/instrumentation_channels/media_assets까지 포함됨
3. data_package 0건의 원인이 source absence인지 parser 누락인지 판정됨
4. parser 누락이면 수정 완료
5. endpoint matrix scheduling이 문서와 구현에서 일치
6. 기본 verify/harness 통과
7. live safety negative 통과
8. data 산출물은 ignored 상태
```

조건을 하나라도 만족하지 못하면 100건 확장을 보류한다.
