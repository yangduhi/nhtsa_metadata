# Codex 작업 프롬프트: 1000건 2011+ Live Pilot 후속 — Schema Backlog Hardening, Endpoint Completeness, Full-Scale Readiness

## 0. 역할과 목표

너는 `D:\vscode\nhtsa_metadata` 프로젝트를 구현·검증하는 Codex agent다.

현재 프로젝트는 2011년 이후 NHTSA vehicle crash/test metadata만 대상으로 하며, `test_date >= 2011-01-01`을 scope 기준으로 사용한다. `test_no` 또는 `modelYear`는 scope 기준으로 사용하지 않는다.

1000건 bounded 2011+ live pilot은 hard gate를 통과했다. 그러나 full crawler로 바로 진행하지 않는다. 이번 작업의 목표는 1000건 pilot 결과를 기반으로 다음 세 가지를 수행하는 것이다.

1. **Endpoint completeness 보강**
   - 기존 1000건 manifest/DB를 대상으로 endpoint coverage gap을 분석한다.
   - 특히 `intrusion_info` coverage가 1000건 pilot에서 2 payload에 그친 원인을 분석하고, endpoint matrix 정책과 맞지 않으면 기존 1000건 manifest 범위 내에서만 bounded live backfill을 수행한다.
   - 새 test_no를 추가 수집하지 않는다.

2. **Schema optimization analyzer 품질 보강**
   - 현재 optimizer가 `curveNo`, `testNo`, `numberofFirstPoint` 같은 identifier/numeric field를 dictionary candidate로 분류하는 문제를 보정한다.
   - `source_field_catalog`의 mapped/unmapped 상태를 실제 canonical mapping과 일치시키고, false unmapped를 줄인다.
   - `source_conflicts=2233`을 conflict taxonomy로 분석한다.
   - `data_package candidates/classified` counting invariant를 명확히 한다.
   - `code_values` 또는 derived dictionary report를 통해 실제 low-cardinality domain 값만 dictionary 후보로 남긴다.

3. **Full-scale readiness gate 작성**
   - full crawler를 실행하지 않는다.
   - 1000건 결과를 기준으로 full 2011+ 수집 전 차단 조건, 허용 조건, schema backlog, operational risk를 문서화한다.
   - 다음 단계가 full crawler인지, 추가 bounded pilot인지, schema migration인지 명확히 판정한다.

---

## 1. 현재 전제

현재 상태는 다음을 전제로 한다.

```text
branch: main
HEAD: 689b96f 또는 그 이후 main commit
1000건 bounded 2011+ live pilot: 통과
full crawler: 미실행
파일 다운로드: 미실행
media fetch: 미실행
waveform/package parsing: 미실행
```

기존 산출물:

```text
data/stratified_live_pilot_2011plus_1000_manifest.csv
data/stratified_live_pilot_2011plus_1000.sqlite
data/schema_audit_report_2011plus_1000.json
data/schema_optimization_report_2011plus_1000.json

docs/phase_reports/1000test_2011plus_live_manifest_review.md
docs/phase_reports/1000test_2011plus_live_pilot_report.md
docs/phase_reports/1000test_2011plus_schema_optimization_report.md
```

`data/` 산출물은 ignored 상태여야 하며 commit하지 않는다.

---

## 2. 승인 범위

이번 작업에서 승인되는 live 작업은 다음으로 제한한다.

```text
승인됨:
- 기존 1000건 manifest 범위 내 endpoint coverage gap 확인
- 기존 1000건 manifest에 포함된 test_no에 대해서만 missing endpoint bounded backfill
- 특히 intrusion_info endpoint scheduling/backfill 검증
- backfill 후 stored raw payload 기반 rebuild
- schema audit 재실행
- schema optimization analyzer 보강 및 재실행

승인되지 않음:
- 새 test_no 추가 수집
- 1000건 초과 collect
- full crawler
- 전체 NHTSA range scan
- 250/3000/all-2011+ collect
- 파일 다운로드
- media URL fetch/download
- waveform/TDMS/UDS/EV/ABF/ISO/ZIP 내부 parsing
- 기본 verify.ps1 또는 .harness/run.ps1에 live API 추가
- data/*.sqlite, data/*.json, data/*.csv commit
- raw payload 전문을 docs에 붙여넣기
```

---

## 3. 사전 검증

다음을 실행한다.

```powershell
git status --short
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
HEAD >= 689b96f 또는 이후 main commit
pytest pass
ruff pass
mypy pass
verify pass
harness pass
기본 verify/harness에 live API 호출 없음
```

사전 검증 실패 시 live/backfill 작업을 시작하지 말고 먼저 수정한다.

---

## 4. 1000건 결과 상세 진단

기존 1000건 DB를 대상으로 진단 명령을 추가하거나 기존 `schema audit`, `schema optimize-analyze`를 확장한다.

권장 명령:

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli schema audit `
  --database-url sqlite:///data/stratified_live_pilot_2011plus_1000.sqlite `
  --output data/schema_audit_report_2011plus_1000_pre_backfill.json `
  --include-duplicate-details `
  --duplicate-detail-limit 50
```

추가 진단 명령을 구현한다면 예시는 다음이다.

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli schema endpoint-completeness `
  --database-url sqlite:///data/stratified_live_pilot_2011plus_1000.sqlite `
  --manifest data/stratified_live_pilot_2011plus_1000_manifest.csv `
  --output data/endpoint_completeness_2011plus_1000.json
```

필수 진단 항목:

```text
- endpoint별 expected_request_count
- endpoint별 actual_payload_count
- endpoint별 missing_request_count
- endpoint별 allowed_empty_count
- endpoint별 non_empty_count
- test_no별 missing endpoint matrix
- vehicle_no별 intrusion_info expected/actual
- occupant별 restraint_info expected/actual
- instrumentation_info page coverage expected/actual
- multimedia_files / vehicle_documents coverage
```

특히 다음 gap을 확인한다.

```text
1000건 report observed:
- intrusion_info actual payloads = 2
- vehicles = 1107
- tests = 1000

판정 필요:
- intrusion_info는 모든 vehicle_no에 대해 호출해야 하는가?
- subject_vehicle에 대해서만 호출해야 하는가?
- barrier/impactor vehicle은 제외해야 하는가?
- 현재 2 payload가 의도된 정책인가 scheduling bug인가?
```

권장 기본 정책:

```text
intrusion_info expected targets =
  all canonical vehicles where participant_kind in ('subject_vehicle', 'other') OR vehicle_no is present and not clearly impactor-only

단, 첫 구현에서는 conservative하게:
  all distinct (test_no, vehicle_no) from vehicles
  except vehicle rows classified as pure impactor_vehicle only if the participant link is unambiguous
```

정책은 문서화한다.

---

## 5. Endpoint completeness backfill

`intrusion_info` 또는 기타 endpoint gap이 endpoint matrix 정책과 불일치하면, 기존 1000건 manifest 범위 내에서만 backfill을 수행한다.

### 5.1 Backfill CLI 추가

다음 CLI를 구현한다.

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog backfill-endpoints `
  --database-url sqlite:///data/stratified_live_pilot_2011plus_1000.sqlite `
  --manifest data/stratified_live_pilot_2011plus_1000_manifest.csv `
  --source live `
  --allow-live `
  --endpoints intrusion_info `
  --scope existing-manifest `
  --only-missing `
  --min-test-date 2011-01-01 `
  --output data/backfill_intrusion_2011plus_1000_report.json
```

필수 safety gate:

```text
--source live
--allow-live
NHTSA_METADATA_ALLOW_LIVE=true
```

필수 제한:

```text
- manifest에 없는 test_no backfill 금지
- test_date < 2011-01-01 backfill 금지
- endpoint 전체 range discovery 금지
- 파일 다운로드 금지
```

### 5.2 실행 명령

backfill이 필요하다고 판정되면 다음을 실행한다.

```powershell
$env:NHTSA_METADATA_ALLOW_LIVE="true"

.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog backfill-endpoints `
  --database-url sqlite:///data/stratified_live_pilot_2011plus_1000.sqlite `
  --manifest data/stratified_live_pilot_2011plus_1000_manifest.csv `
  --source live `
  --allow-live `
  --endpoints intrusion_info `
  --scope existing-manifest `
  --only-missing `
  --min-test-date 2011-01-01 `
  --output data/backfill_intrusion_2011plus_1000_report.json
```

Backfill 후 rebuild:

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog rebuild `
  --database-url sqlite:///data/stratified_live_pilot_2011plus_1000.sqlite
```

Audit 재실행:

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli schema audit `
  --database-url sqlite:///data/stratified_live_pilot_2011plus_1000.sqlite `
  --output data/schema_audit_report_2011plus_1000_after_backfill.json `
  --include-duplicate-details `
  --duplicate-detail-limit 50
```

### 5.3 Backfill acceptance

```text
- no new test_no added
- canonical tests = 1000
- scope violations = 0
- duplicate groups 7종 = 0
- semantic hard failures = 0
- intrusion_info expected/actual documented
- intrusion_info missing_request_count = 0 또는 accepted_policy_exception
- intrusion empty HTTP/API 200 responses stored as source_payloads
- collection_run_items clearly marked backfill
- files not downloaded
```

---

## 6. Schema optimizer 품질 보강

현재 1000건 optimizer 결과는 P0/P1이 0이지만, 다음 품질 이슈가 있다.

```text
- mapped fields = 10, unmapped = 287로 실제 canonical mapping 대비 mapped status가 과소 기록된 가능성
- instrumentation_info의 curveNo/testNo/numberofFirstPoint 등이 dictionary_candidate로 제안됨
- code_values = 0인데 dictionary candidates = 137
- source_conflicts = 2233인데 conflict taxonomy가 보고되지 않음
- data_package candidates/classified count invariant가 불명확함
- test_facets = 297로 필수 facet coverage가 부족할 수 있음
- unknown:needs_review classification = 105
```

### 6.1 Field mapping reconciliation

다음 로직을 구현한다.

```text
- source_field_catalog field_path와 alias map을 비교
- canonical mapper에서 실제 사용한 field를 mapped로 표시
- mapped_table, mapped_column을 채움
- row-level lineage와 source_row_path를 통해 field 사용 evidence를 남김
- extra_json에 반복 저장되는 field는 extra_json_fields로 분리
```

필수 alias coverage 보강 후보:

```text
instrumentation_info:
- $.results[*].axisDirofSensor -> instrumentation_channels.sensor_axis
- $.results[*].curveNo -> instrumentation_channels.curve_no
- $.results[*].dataMeasurementUnits -> instrumentation_channels.unit
- $.results[*].dataStatus -> instrumentation_channels.data_status
- $.results[*].instrumentationCommentary -> instrumentation_channels.commentary
- $.results[*].numberofFirstPoint -> instrumentation_channels.first_point
- $.results[*].numberofLastPoint -> instrumentation_channels.last_point
- $.results[*].sensorAttachment -> instrumentation_channels.sensor_attachment
- $.results[*].sensorType -> instrumentation_channels.sensor_type
- $.results[*].timeIncrement -> instrumentation_channels.time_increment
- $.results[*].channelStatus -> instrumentation_channels.channel_status
- $.results[*].vehicleNo -> instrumentation_channels.vehicle_no

occupant_info:
- $.results[*].vehicleNo -> occupants.vehicle_no
- $.results[*].occupantLocation -> occupants.occupant_location
- $.results[*].occupantType -> occupants.occupant_type
- injury metric fields -> injury_metrics

restraint_info:
- $.results[*].vehicleNo -> restraints.vehicle_no
- occupantLocation from request path -> restraints.occupant_location
- restraint type/deployment fields -> restraints.*

vehicle_info:
- $.results[*].vehicleNo -> vehicles.vehicle_no
- make/model/year/speed/weight -> vehicles.*

barrier_info:
- rigidity/shape/angle/commentary -> barriers.*
```

### 6.2 Dictionary candidate classifier 개선

`dictionary_candidate`에서 다음 field는 제외하거나 별도 class로 분류한다.

```text
identifier_field:
- testNo
- vehicleNo
- curveNo
- source row id
- URL/hash/path fields

numeric_measurement_field:
- numberofFirstPoint
- numberofLastPoint
- timeIncrement
- speed
- weight
- length
- width
- HIC/femur/load/metric values
```

실제 dictionary 후보는 다음처럼 low-cardinality domain field 중심으로 제한한다.

```text
- sensorType
- sensorAttachment
- axisDirofSensor
- dataMeasurementUnits
- dataStatus
- channelStatus
- occupantLocation
- occupantType
- restraint type/deployment
- barrier rigidity/shape
- asset_kind
- asset_subtype
- test_configuration_key
- test_type normalized category
```

추천 class를 확장한다.

```text
identifier_no_action
numeric_measurement_column_candidate
dictionary_candidate
code_values_candidate
facet_candidate
index_candidate
raw_only_no_action
requires_manual_review
```

### 6.3 code_values population 또는 dictionary report

`code_values` 테이블이 운영 목적이라면, 다음 중 하나를 구현한다.

권장 A: derived dictionary upsert

```text
code_values:
- code_system
- code
- display_value
- normalized_value
- source_endpoint_name
- source_field_path
- observed_count
- observed_test_count
- first_seen_at
- last_seen_at
- status
```

대상:

```text
sensorType
sensorAttachment
axisDirofSensor
dataMeasurementUnits
dataStatus
channelStatus
occupantLocation
occupantType
restraintType
restraintDeployment
barrierRigidity
barrierShape
assetKind
assetSubtype
testConfigurationKey
classificationStatus
participantKind
```

권장 B: DB 테이블은 아직 비워두되, `schema_optimization_report`에 dictionary domain tables를 별도 출력한다.

둘 중 하나를 선택하고 문서화한다. A를 선택하면 Alembic migration이 필요한지 확인한다.

### 6.4 source_conflicts taxonomy

`source_conflicts=2233`을 다음 taxonomy로 분류한다.

```text
benign_format_difference
benign_alias_difference
numeric_rounding_difference
unit_representation_difference
endpoint_precedence_expected
canonical_resolution_needed
semantic_conflict
requires_manual_review
```

Conflict report 필드:

```json
{
  "field_semantic_key": "...",
  "test_no": 10001,
  "endpoint_a": "...",
  "endpoint_b": "...",
  "value_a_sample": "...",
  "value_b_sample": "...",
  "conflict_class": "...",
  "resolution_policy": "...",
  "priority": "P0|P1|P2|P3"
}
```

P0/P1 판정:

```text
P0:
- scope field conflict causing wrong inclusion/exclusion
- test_no/date identity conflict
- semantic over-merge/over-split risk

P1:
- user-facing filter value conflict
- canonical summary value conflict without resolution policy
```

### 6.5 data_package audit invariant

현재 report에서 다음처럼 불일치가 관측될 수 있다.

```text
data_package candidates: 4960
classified data packages: 4963
```

다음을 명확히 하라.

```text
candidate_count definition
classified_count definition
classified_not_candidate_count
candidate_unclassified_count
```

권장 invariant:

```text
classified_data_packages <= data_package_candidates
unclassified_asset_candidates = data_package_candidates - classified_data_packages
```

만약 classified count가 candidates보다 클 수 있는 정의라면, 이름을 바꾼다.

```text
data_package_candidate_assets
classified_data_package_assets
classified_non_candidate_assets
```

### 6.6 test_facets/read-model coverage audit

필수 facet coverage를 점검한다.

필수 facet 후보:

```text
test_type
test_configuration
test_configuration_key
test_family
classification_status
vehicle_make
vehicle_model
model_year
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
channel_status
data_status
injury_metric_code
deformation_code
asset_kind
asset_subtype
has_uds_or_tdms_package
```

`test_facets` row 수가 1000건 DB에서 297 수준이면 의도된 설계인지 부족한지 판정한다.

필요 시 read model builder를 확장한다.

---

## 7. Test classification 보강

현재 1000건 distribution에 `unknown:needs_review=105`가 있다. 이를 분석한다.

목표:

```text
- unknown:needs_review row를 endpoint/test_type/test_configuration/title 기반으로 분류 가능 여부 확인
- 불가능하면 reason_code를 부여해 manual review 대상으로 남김
- 무리하게 crash family로 오분류하지 않음
```

분류 taxonomy 보강 후보:

```text
frontal_barrier
side_impactor
side
rear
rollover
sled_with_body
sled_without_body
static_airbag
low_risk_deployment
pedestrian
child_restraint
adas_fcw
adas_ldw
adas_other
calibration
research_other
unknown_needs_review
```

보고 항목:

```text
- unknown before/after count
- newly classified count
- still unknown count
- top unknown test_configuration/test_type/title patterns
- classification rule added
- false-positive risk
```

---

## 8. Balance status 개선

1000건 manifest에서 `relaxed_missing_year=1000`이 모든 row에 붙는 것은 해석성이 낮다.

수정 목표:

```text
manifest-level balance_status:
- strict
- relaxed
- failed

manifest-level relax_reason:
- missing_year_coverage: [2026]
- insufficient_candidates_by_year
- insufficient_candidates_by_type_year

row-level selection_reason:
- anchor
- type_year_balanced
- type_first_backfill
- relaxed_backfill
```

기존 column이 있다면 backward compatibility를 유지한다.
문서에서 기존 `relaxed_missing_year` 의미를 설명하고 새 구조로 개선한다.

---

## 9. Operations hardening

### 9.1 Interrupted run finalization

1000건 collect에서 첫 장시간 run이 tool timeout으로 중단되어 `collection_runs`에 `started=1`이 남았다.

다음 중 하나를 구현한다.

```text
- catalog resume 시작 시 stale started run을 interrupted/abandoned로 mark
- schema audit에서 stale run age를 warning으로 보고
- collection run status taxonomy에 interrupted 추가
```

Acceptance:

```text
collection_runs에 오래된 started 상태가 남아 있지 않음
또는 audit에서 known interrupted run으로 명확히 보고됨
```

### 9.2 Resume metrics 명확화

보고서에서 다음을 분리한다.

```text
manifest_tests = 1000
newly_collected_items
skipped_existing_items
final_canonical_tests
backfill_items
```

`collection_run_items=1389`가 최종 test count와 혼동되지 않도록 phase report를 수정한다.

---

## 10. Reports

다음 문서를 생성 또는 갱신한다.

```text
docs/phase_reports/1000test_2011plus_endpoint_completeness_report.md
docs/phase_reports/1000test_2011plus_schema_backlog_report.md
docs/phase_reports/1000test_2011plus_full_scale_readiness_gate.md
```

### 10.1 Endpoint completeness report

포함:

```text
- endpoint별 expected/actual/missing
- intrusion_info gap 판정
- backfill 실행 여부
- backfill 후 source_payload count 변화
- canonical/rebuild 영향
- remaining accepted exceptions
```

### 10.2 Schema backlog report

포함:

```text
- field mapping reconciliation 결과
- false unmapped 감소량
- dictionary candidate classifier 보정 전/후
- code_values 또는 dictionary report 결과
- source_conflicts taxonomy 결과
- data_package counting invariant 결과
- test_facets/read-model coverage 결과
- test_classification unknown 개선 결과
- P0/P1/P2/P3 backlog
```

### 10.3 Full-scale readiness gate

포함:

```text
- full crawler 진입 여부: yes/no
- blockers
- warnings
- accepted risks
- required migrations before full scale
- required operational limits
- recommended next bounded size, if any
```

판정 기준:

```text
Full-scale readiness = pass only if:
- endpoint completeness has no unexplained missing matrix
- scope violations = 0
- duplicate groups = 0
- semantic hard failures = 0
- P0 schema recommendations = 0
- P1 schema recommendations are either fixed or explicitly accepted
- stale collection runs resolved or documented
- data package audit invariant holds
- source conflict P0/P1 = 0 or resolved
- verify/harness remain fixture-only
```

---

## 11. Safety negative 재검증

작업 후 다음을 실행한다.

```powershell
Remove-Item Env:\NHTSA_METADATA_ALLOW_LIVE -ErrorAction SilentlyContinue

.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog build-manifest `
  --source live `
  --output data\should_not_exist.csv `
  --limit 5 `
  --min-test-date 2011-01-01

.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog build-manifest `
  --source live `
  --allow-live `
  --output data\should_not_exist.csv `
  --limit 5 `
  --min-test-date 2011-01-01
```

성공 기준:

```text
둘 다 실패
exit code non-zero
data\should_not_exist.csv 생성 안 됨
```

Backfill CLI도 negative test를 추가한다.

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog backfill-endpoints `
  --database-url sqlite:///data/stratified_live_pilot_2011plus_1000.sqlite `
  --manifest data/stratified_live_pilot_2011plus_1000_manifest.csv `
  --source live `
  --endpoints intrusion_info `
  --scope existing-manifest `
  --only-missing `
  --output data\should_not_exist_backfill.json
```

`--allow-live` 또는 env var가 없으면 실패해야 하고 output이 생성되면 안 된다.

---

## 12. 최종 검증

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check src tests
.venv\Scripts\python.exe -m mypy src\nhtsa_metadata
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
powershell -ExecutionPolicy Bypass -File .harness\run.ps1
```

성공 기준:

```text
pytest pass
ruff pass
mypy pass
verify pass
harness pass
기본 verify/harness에 live API 없음
```

---

## 13. Git 처리

브랜치:

```powershell
git checkout main
git pull --ff-only
git checkout -b codex/1000test-schema-backlog-hardening
```

커밋 허용 대상:

```text
src/
tests/
docs/
instructions/
alembic/  # migration을 추가한 경우
.env.example
pyproject.toml
```

커밋 금지 대상:

```text
data/*.csv
data/*.sqlite
data/*.json
raw payload dump
downloaded files
media/data package contents
```

커밋:

```powershell
git add src tests docs instructions alembic .env.example pyproject.toml
git commit -m "fix: harden 1000 test schema backlog analysis"
git push origin codex/1000test-schema-backlog-hardening
```

main merge/push는 프로젝트 운영 방식에 맞춰 fast-forward로 진행한다.
data 산출물이 staged되면 즉시 중단한다.

---

## 14. Stop conditions

다음 중 하나라도 발생하면 full-scale readiness를 pass로 보고하지 말고 중단/보고한다.

```text
new test_no가 수집됨
canonical tests != 1000 after backfill/rebuild
scope violations > 0
duplicate groups > 0
semantic hard failures > 0
intrusion_info missing_request_count > 0 without accepted policy
restraint_info missing_request_count > 0
data_package counting invariant fails
source conflict P0 > 0
schema optimizer P0 > 0
schema optimizer P1 unresolved > 0
default verify/harness에 live API가 들어감
data artifacts가 git tracked/staged됨
파일 다운로드 실행됨
full crawler 실행됨
```

---

## 15. 최종 보고 형식

작업 완료 후 다음 형식으로 보고한다.

```text
결론:
- endpoint completeness remediation 통과 / 부분 통과 / 실패
- schema backlog hardening 통과 / 부분 통과 / 실패
- full-scale readiness: pass / blocked / conditional
- full crawler 실행 여부
- 파일 다운로드 여부

실행 범위:
- 기존 1000 manifest만 사용했는지
- 새 test_no 수집 여부
- backfill endpoint
- live backfill 실행 여부
- DB path
- audit path
- schema backlog report path

Endpoint completeness:
- endpoint별 expected/actual/missing
- intrusion_info expected/actual/missing
- backfill source_payload 증가량
- remaining accepted exceptions

Schema optimizer:
- field profile count
- mapped/unmapped before/after
- dictionary candidates before/after
- identifier/numeric fields reclassified count
- code_values or dictionary report result
- source_conflicts taxonomy P0/P1/P2/P3
- data_package invariant result
- test_facets coverage result
- test_classification unknown before/after

Audit:
- scope violations
- duplicate groups
- semantic hard failures
- restraint_info expected/actual/missing
- intrusion_info expected/actual/missing
- data_package candidates/classified/unclassified

검증:
- pytest
- ruff
- mypy
- verify
- harness
- live safety negative
- backfill safety negative

Git:
- branch
- commit
- status
- push 여부
- data artifacts ignored 여부

후속:
- full-scale 2011+ crawler를 바로 진행해도 되는지
- 아니면 추가 bounded pilot/마이그레이션/분류 보강이 필요한지
- schema migration backlog
```
