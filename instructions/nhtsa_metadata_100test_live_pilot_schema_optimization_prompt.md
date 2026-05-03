# Codex 작업 프롬프트: 100건 bounded 2011+ live pilot 수집 및 schema optimization 분석

## 0. 역할과 목표

너는 `D:\vscode\nhtsa_metadata` 프로젝트를 구현·검증하는 Codex agent다.

이번 작업은 **승인된 100건 bounded 2011+ live pilot**이다.  
목표는 다음 세 가지다.

1. NHTSA live by-search를 사용해 **2011년 이후 test_date 기준 100건 manifest**를 생성한다.
2. 생성된 live manifest가 acceptance 조건을 만족하면 **100건 bounded live collect**를 실행한다.
3. 수집된 live raw/canonical/read-model 데이터를 분석해 **DB schema 최적화 후보를 산출하는 로직**을 구현하고, 이번 100건 DB에 적용해 보고서를 만든다.

이 작업은 full crawler가 아니다.  
파일 다운로드가 아니다.  
waveform, TDMS, UDS, EV, ABF, ISO, ZIP 내부 분석이 아니다.  
data package는 URL/metadata registry로만 저장한다.

---

## 1. 승인 범위

이번 프롬프트에서 승인된 live 작업은 아래에 한정한다.

```text
승인됨:
- 100건 live manifest build
- 100건 bounded live collect
- endpoint matrix metadata 수집
- schema audit
- scale/API smoke
- live safety negative test
- 수집된 live metadata 기반 schema optimization analysis

승인되지 않음:
- full crawler
- 250건 pilot
- 100건 초과 collect
- 파일 다운로드
- waveform/TDMS/UDS/EV/ABF/ISO/ZIP 내부 파싱
- 기본 verify.ps1 또는 .harness/run.ps1에 live API 추가
- data/ 산출물 commit
```

---

## 2. 현재 전제

현재 상태는 다음을 전제로 한다.

```text
branch: main
최소 required commit: 6c6f32d 또는 그 이후 main commit
semantic remediation baseline: e2eb298 이후
40건 2011+ semantic remediation: 통과
100건 bounded manifest planning: 통과
full crawler: 미실행
파일 다운로드: 미실행
```

기존 planning 산출물:

```text
docs/phase_reports/2026-04-30__100-test-pilot__pass__100test-2011plus-manifest-plan.md
docs/phase_reports/2026-04-30__100-test-pilot__pass__100test-2011plus-acceptance-matrix.md
instructions/nhtsa_metadata_100test_2011plus_manifest_planning_work_order.md
data/stratified_live_pilot_2011plus_100_manifest_candidate.csv  # ignored, reference DB seed only
```

candidate manifest는 canonical source가 아니다.  
live by-search 검증 후 live manifest를 새로 만들어야 한다.

---

## 3. 절대 금지 사항

다음을 하지 마라.

```text
- full crawler 구현 또는 실행
- 250건 또는 그 이상의 pilot 실행
- NHTSA test_no 전체 range scan
- test_no를 2011+ scope 기준으로 사용
- modelYear를 2011+ scope 기준으로 사용
- 파일 다운로드
- media URL fetch/download
- data package 내부 파일 분석
- waveform/TDMS/UDS/EV/ABF/ISO/ZIP parsing
- 기본 verify/harness에 live API 호출 추가
- data/*.sqlite, data/*.json, data/*.csv 산출물 commit
- raw payload 전문을 docs/phase_reports에 붙여넣기
- schema optimization 추천을 자동 migration으로 즉시 적용
```

schema optimization은 이번 단계에서 **분석·추천·보고**까지 한다.  
canonical schema 변경은 P0 데이터 손실/의미 손상 버그가 발견된 경우에만 최소 보정하고, 일반적인 컬럼/인덱스/lookup 승격은 보고서의 recommendation으로 남긴다.

---

## 4. 사전 검증

먼저 다음을 실행한다.

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
HEAD >= 6c6f32d 또는 이후 main commit
pytest pass
ruff pass
mypy pass
verify.ps1 pass
.harness/run.ps1 pass
기본 verify/harness에 live API 호출 없음
```

사전 검증 실패 시 live 작업을 시작하지 말고 실패 원인을 수정한다.

---

## 5. 100건 live manifest build

### 5.1 실행 명령

```powershell
$env:NHTSA_METADATA_ALLOW_LIVE="true"

.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog build-manifest `
  --source live `
  --allow-live `
  --output data\stratified_live_pilot_2011plus_100_manifest.csv `
  --limit 100 `
  --max-per-configuration 20 `
  --min-test-date 2011-01-01 `
  --reference-database D:\vscode\pulse_analysis\data\db\nhtsa_data.db
```

### 5.2 live manifest review

생성 후 즉시 다음을 확인한다.

```text
manifest rows = 100
duplicate test_no = 0
all test_date >= 2011-01-01
all scope_status = in_scope
missing test_date = 0
parse failed test_date = 0
10001 included
10003 included
7201 included
max normalized configuration bucket <= 20
data/stratified_live_pilot_2011plus_100_manifest.csv exists
```

candidate manifest와 live manifest의 차이를 요약한다.

비교 필드:

```text
test_no
test_date
test_configuration
test_configuration_key
test_type
model_year
vehicle_make
vehicle_model
scope_status
```

live manifest에 pre-2011, missing date, parse failed date, duplicate test_no, anchor missing이 있으면 **collect를 실행하지 말고 중단**한다.

### 5.3 manifest review report

다음 문서를 생성 또는 갱신한다.

```text
docs/phase_reports/2026-04-30__100-test-pilot__recorded__100-test-2011-plus-live-manifest-review.md
```

포함할 내용:

```text
- 명령
- row count
- date range
- anchors 포함 여부
- configuration bucket 분포
- year bucket 분포
- candidate vs live discrepancy 요약
- rejected row count
- accepted row count
- collect 진행 가능 여부
```

raw payload 전문은 문서에 넣지 않는다.

---

## 6. 100건 bounded live collect

manifest acceptance가 통과하면 collect를 실행한다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\live_pilot_validate.ps1 `
  -AllowLive `
  -DatabaseUrl sqlite:///data/stratified_live_pilot_2011plus_100.sqlite `
  -Manifest data/stratified_live_pilot_2011plus_100_manifest.csv
```

이 script가 이미 collect, coverage, schema audit, scale report, API smoke를 묶는다면 그대로 사용한다.  
누락된 경우 아래 schema audit을 별도로 실행한다.

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli schema audit `
  --database-url sqlite:///data/stratified_live_pilot_2011plus_100.sqlite `
  --output data/schema_audit_report_2011plus_100.json `
  --include-duplicate-details `
  --duplicate-detail-limit 50
```

---

## 7. 100건 pilot acceptance

다음 조건을 모두 확인한다.

### 7.1 Collection

```text
collection run items = 100
failed collection items = 0 또는 documented allowed transient only
source_payloads > 0
source_payload_observations > 0
all source payloads have endpoint_name
all expected paginated instrumentation pages collected
allowed empty endpoints not treated as failure
```

### 7.2 Scope

```text
scope violations = 0
read-model out-of-scope rows = 0
missing canonical test_date = 0
date parse failure canonical rows = 0
canonical tests = 100
test_filter_summary = 100
```

### 7.3 Duplicate / semantic

Duplicate groups must be 0 for:

```text
vehicles
test_participants
barriers
occupants
restraints
instrumentation_channels
media_assets
```

Semantic hard failures:

```text
semantic hard failures = 0
occupants are normalized occupant slots
restraints preserve occupant context
occupant-specific restraint context loss = 0
barrier semantic status not investigate for baseline tests
restraint_info expected/actual payloads match
restraint_info missing requests = 0
```

### 7.4 Baseline

```text
10001:
- vehicles = 1
- barriers = 1
- occupants = 2
- restraints = 6
- instrumentation_channels >= 634
- media_assets present
- barrier semantic status = fixed or pass
- restraint context loss = 0

10003:
- vehicles >= 2
- participant pattern includes subject_vehicle + impactor_vehicle
- barriers = 0 allowed
- occupants = 2
- restraints >= 6
- instrumentation_channels >= 63
- media_assets present
- restraint context loss = 0

7201:
- test_date >= 2011-01-01
- scope_status = in_scope
- canonical test exists
```

### 7.5 Asset

```text
data_package candidates = classified_data_packages
unclassified_asset_candidates = 0
files are not downloaded
asset registry stores URL/metadata only
```

### 7.6 Field coverage

```text
wildcard path normalization present, e.g. $.results[*].axisDirofSensor
unmapped field count reported
new unmapped critical fields identified
no mapped field regression
```

---

## 8. DB schema optimization analysis 로직 구현

이번 작업의 추가 핵심 요구사항이다.  
100건 live data에서 얻은 field coverage, raw payload, canonical/read-model row, conflicts, extra_json, facets를 분석해 **schema 구성 최적화 후보**를 산출하는 로직을 구현한다.

### 8.1 새 CLI

다음 CLI를 구현한다. 기존 명령 구조에 맞춰 이름은 조정해도 되지만, 기능은 동일해야 한다.

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli schema optimize-analyze `
  --database-url sqlite:///data/stratified_live_pilot_2011plus_100.sqlite `
  --output data/schema_optimization_report_2011plus_100.json `
  --markdown-output docs/phase_reports/2026-04-30__100-test-pilot__recorded__100-test-2011-plus-schema-optimization-report.md `
  --min-test-support 5 `
  --min-non-null-ratio 0.10 `
  --max-dictionary-distinct-ratio 0.25 `
  --include-index-candidates `
  --include-column-candidates `
  --include-facet-candidates
```

명령명이 이미 충돌하면 `schema analyze-live`, `schema optimization-report` 등으로 구현해도 된다.  
단, 최종 보고에서 실제 명령명을 명시한다.

### 8.2 분석 대상

분석 입력:

```text
source_field_catalog
source_payloads
source_payload_sections
source_payload_observations
canonical_row_sources
source_conflicts
tests
vehicles
test_participants
barriers
occupants
restraints
instrumentation_channels
instrumentation_channel_details
injury_metrics
deformation_measurements
intrusion_measurements
media_assets
test_filter_summary
test_facets
asset_summary
code_values
```

특히 다음을 비교한다.

```text
1. source_field_catalog field_path vs canonical mapped columns
2. endpoint/section별 unmapped field 빈도
3. extra_json에 반복적으로 남는 field
4. low-cardinality repeated values
5. type stability / type conflict
6. null/missing ratio
7. source endpoint 간 값 충돌
8. canonical semantic key가 과도하게 merge/split되는 패턴
9. facet/read-model에 자주 필요한데 canonical column이 없는 값
10. field path wildcard normalization 상태
11. large table row counts and likely index needs
```

### 8.3 Field profile 산출

각 field path별로 최소 다음 profile을 산출한다.

```json
{
  "endpoint_name": "...",
  "section_name": "...",
  "field_path": "$.results[*].sensorType",
  "mapping_status": "mapped|unmapped|extra_json|unknown",
  "mapped_table": "...",
  "mapped_column": "...",
  "observed_payload_count": 0,
  "observed_test_count": 0,
  "non_null_count": 0,
  "null_count": 0,
  "missing_estimate": 0,
  "non_null_ratio": 0.0,
  "observed_types": ["string"],
  "type_stability_ratio": 1.0,
  "distinct_count": 0,
  "distinct_ratio": 0.0,
  "example_values": [],
  "first_seen_at": "...",
  "last_seen_at": "...",
  "recommendation_class": "...",
  "recommendation_priority": "P0|P1|P2|P3",
  "recommendation_reason": "..."
}
```

`example_values`는 raw payload 전문이 아니라 짧은 sample value만 허용한다.  
URL은 필요하면 hostname/path 일부만 저장한다. 대용량 JSON은 넣지 않는다.

### 8.4 Recommendation class

다음 recommendation class를 지원한다.

```text
column_candidate
facet_candidate
dictionary_candidate
alias_map_candidate
semantic_key_candidate
index_candidate
read_model_summary_candidate
conflict_resolution_candidate
raw_only_no_action
requires_manual_review
```

기준 예시:

```text
column_candidate:
- observed_test_count >= 5 또는 전체 test의 10% 이상
- non_null_ratio >= 0.10
- type_stability_ratio >= 0.95
- 현재 unmapped 또는 extra_json에 반복 저장됨
- engineering filter/domain value일 가능성이 있음

dictionary_candidate:
- distinct_count between 2 and 100
- distinct_ratio <= 0.25
- 반복 value가 code/value domain으로 보임

facet_candidate:
- user-facing filter에 유용
- low/medium cardinality
- test_filter_summary 또는 test_facets로 승격 가능

index_candidate:
- 기존 API/filter가 자주 사용하는 column
- row count가 커지고 있음
- selectivity가 너무 낮지 않음
- payload_json 전체 index는 금지

semantic_key_candidate:
- duplicate group은 0이지만 semantic over-merge/over-split 의심
- source_conflicts 또는 baseline semantic audit에서 반복 issue 발생

alias_map_candidate:
- 같은 의미의 field가 endpoint/section별 다른 이름으로 반복됨
- 예: metadata code vs API label

raw_only_no_action:
- low support
- high variability
- value semantics 불명확
- endpoint-specific commentary
```

### 8.5 Scoring

간단한 deterministic scoring을 구현한다.

예시:

```text
support_score = min(observed_test_count / total_tests, 1.0)
non_null_score = non_null_ratio
type_score = type_stability_ratio
dictionary_score = 1 - min(distinct_ratio, 1.0)
conflict_penalty = 0.3 if conflict observed else 0
mapped_bonus = -0.2 if already mapped else 0
engineering_bonus = 0.2 if field belongs to barrier/restraint/instrumentation/injury/deformation/media/test classification endpoint else 0

promotion_score =
  support_score * 0.30
  + non_null_score * 0.20
  + type_score * 0.20
  + dictionary_score * 0.10
  + engineering_bonus
  - conflict_penalty
  + mapped_bonus
```

Priority:

```text
P0:
- data loss risk
- scope violation risk
- semantic over-merge/over-split risk
- raw-only state hides required domain value

P1:
- high support unmapped field useful for filtering or canonical model

P2:
- useful dictionary/facet/index candidate

P3:
- low-risk documentation or alias cleanup
```

### 8.6 Report JSON structure

`data/schema_optimization_report_2011plus_100.json` 구조:

```json
{
  "run": {
    "created_at": "...",
    "database_url_redacted": "...",
    "manifest_path": "data/stratified_live_pilot_2011plus_100_manifest.csv",
    "test_count": 100,
    "min_test_date": "2011-01-01",
    "software_version": "...",
    "git_commit": "..."
  },
  "summary": {
    "field_profiles": 0,
    "mapped_fields": 0,
    "unmapped_fields": 0,
    "extra_json_fields": 0,
    "column_candidates": 0,
    "facet_candidates": 0,
    "dictionary_candidates": 0,
    "index_candidates": 0,
    "semantic_key_candidates": 0,
    "p0_recommendations": 0,
    "p1_recommendations": 0,
    "p2_recommendations": 0,
    "p3_recommendations": 0
  },
  "endpoint_coverage": [],
  "table_growth": [],
  "field_profiles": [],
  "recommendations": [],
  "manual_review_items": [],
  "no_action_raw_only": []
}
```

### 8.7 Markdown report structure

`docs/phase_reports/2026-04-30__100-test-pilot__recorded__100-test-2011-plus-schema-optimization-report.md`를 작성한다.

필수 섹션:

```text
# 100-Test 2011+ Schema Optimization Report

## Scope
- 100건 bounded live pilot DB 기반
- 2011+ only
- no full crawler
- no file download
- no waveform/package parsing

## Input DB Summary
- tests
- source_payloads
- source_payload_observations
- canonical table counts
- read model counts

## Field Coverage Summary
- mapped/unmapped/extra_json counts
- top unmapped endpoints
- top repeated unmapped field paths
- wildcard path normalization examples

## Recommendation Summary
- P0/P1/P2/P3 counts
- column candidates
- dictionary candidates
- facet candidates
- index candidates
- alias map candidates
- semantic key candidates

## Proposed Schema Optimization Backlog
- immediate fix candidates
- next migration candidates
- read-model/facet candidates
- code_values/dictionary candidates
- keep raw-only candidates

## Do Not Change Yet
- high variability fields
- low support fields
- ambiguous commentary fields
- file/data package internals

## Decision
- 100건 pilot schema is acceptable / partially acceptable / failed
- Whether 250-test planning can begin
```

문서에는 raw payload 전문을 넣지 않는다.

### 8.8 DB persistence 선택 사항

가능하면 다음 derived analysis tables를 추가한다.  
시간이 부족하거나 migration 리스크가 크면 JSON/Markdown report만 구현해도 된다.

```text
schema_analysis_runs
schema_field_profiles
schema_optimization_recommendations
```

추가하는 경우:

```text
- Alembic migration 추가
- docs/2026-04-28__schema__current__db-schema.md 갱신
- docs/2026-04-28__contract__current__db-schema-contract.md 갱신
- tests 추가
```

단, 이 테이블은 derived/read-model 성격이다. source of truth가 아니다.

---

## 9. 100건 live pilot report

다음 문서를 생성한다.

```text
docs/phase_reports/2026-04-30__100-test-pilot__recorded__100-test-2011-plus-live-pilot-report.md
```

포함할 내용:

```text
결론:
- 통과 / 부분 통과 / 실패
- 250건 planning 진행 가능 여부
- full crawler 실행 여부
- 파일 다운로드 여부

실행 범위:
- live manifest build 여부
- live collect 여부
- manifest path
- database path
- audit path
- schema optimization report path

Manifest:
- rows
- date range
- anchors
- configuration distribution
- year bucket distribution
- candidate vs live discrepancy

Collection:
- collection_run_items
- succeeded/failed/skipped
- source_payloads
- source_payload_observations
- endpoint coverage

Canonical/read-model:
- tests
- vehicles
- participants
- barriers
- occupants
- restraints
- instrumentation_channels
- media_assets
- test_filter_summary

Audit:
- scope violations
- duplicate groups
- semantic hard failures
- data_package candidates/classified
- restraint_info expected/actual/missing
- unmapped field count

Baseline:
- 10001
- 10003
- 7201

Schema optimization:
- recommendation counts by priority/class
- P0/P1 items
- proposed next migration candidates
- raw-only no-action count

Safety:
- live safety negative result
- verify/harness fixture-only result
- data artifacts ignored

Git:
- branch
- commit
- status
- push 여부
```

---

## 10. Safety negative 재검증

100건 live collect 후에도 safety gate가 유지되는지 검증한다.

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

그 다음 env var를 복구해야 하면 명시적으로 다시 설정한다.

---

## 11. 최종 검증

모든 코드/문서 수정 후 다음을 실행한다.

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

## 12. Git 처리

브랜치:

```powershell
git checkout main
git pull --ff-only
git checkout -b codex/100test-live-pilot-schema-optimization
```

커밋 대상:

```text
허용:
- src/ 코드
- tests/
- docs/
- instructions/
- alembic migration, 추가한 경우

금지:
- data/*.csv
- data/*.sqlite
- data/*.json
- raw payload dump
- downloaded files
```

마지막 확인:

```powershell
git status --short
```

커밋:

```powershell
git add src tests docs instructions alembic .env.example pyproject.toml
git commit -m "feat: run 100 test live pilot schema optimization"
git push origin codex/100test-live-pilot-schema-optimization
```

main merge/push는 프로젝트 운영 방식에 맞춰 fast-forward로 진행한다.  
단, data 산출물이 커밋 대상에 잡히면 즉시 중단한다.

---

## 13. Stop conditions

아래 중 하나라도 발생하면 100건 collect 또는 다음 단계로 진행하지 말고 보고한다.

```text
manifest rows != 100
manifest에 pre-2011 row 존재
manifest에 missing/parse failed test_date 존재
10001/10003/7201 anchor 누락
duplicate test_no > 0
collect failed items가 허용 transient를 초과
scope violations > 0
read-model out-of-scope rows > 0
duplicate groups > 0
semantic hard failures > 0
restraint context loss > 0
restraint_info missing requests > 0
data_package candidates != classified data_packages
unclassified_asset_candidates > 0
schema optimizer에서 P0 data loss recommendation 발생
기본 verify/harness에 live API가 들어감
data artifacts가 git tracked로 잡힘
파일 다운로드가 실행됨
full crawler가 실행됨
```

P0 schema optimization recommendation이 발생하면 250건 planning으로 가지 않는다.  
P1 이하만 있으면 250건 planning 가능 여부를 보고서에서 판단한다.

---

## 14. 최종 보고 형식

작업 완료 후 아래 형식으로 보고한다.

```text
결론:
- 100건 bounded 2011+ live pilot 통과 / 부분 통과 / 실패
- schema optimization analysis 통과 / 부분 통과 / 실패
- 250건 planning 진행 가능 여부
- full crawler 실행 여부
- 파일 다운로드 여부

실행:
- live manifest build: 예/아니오
- live collect: 예/아니오
- manifest path
- DB path
- audit path
- schema optimization report path

Manifest:
- rows
- date range
- 10001/10003/7201 포함 여부
- duplicate test_no
- max configuration bucket
- candidate vs live discrepancy summary

Collection/Audit:
- collection run items
- source_payloads
- source_payload_observations
- canonical tests
- test_filter_summary
- instrumentation_channels
- media_assets
- scope violations
- duplicate groups
- semantic hard failures
- data_package candidates/classified
- restraint_info expected/actual/missing

Baseline:
- 10001 vehicles/barriers/occupants/restraints/instrumentation/media
- 10003 vehicles/participants/barriers/occupants/restraints/instrumentation/media
- 7201 scope/canonical status

Schema optimization:
- field profile count
- mapped/unmapped/extra_json counts
- recommendation counts by class
- P0/P1/P2/P3 counts
- top 10 schema recommendations
- next migration candidates
- no-action raw-only count

Safety:
- --allow-live 누락 실패 여부
- NHTSA_METADATA_ALLOW_LIVE 누락 실패 여부
- failed safety output 미생성 여부
- verify/harness fixture-only 유지 여부

검증:
- pytest
- ruff
- mypy
- scripts/verify.ps1
- .harness/run.ps1

Git:
- branch
- commit
- status
- push 여부
- data artifacts ignored 여부

후속:
- 250건 bounded pilot planning 가능 여부
- full crawler는 계속 보류할지 여부
- schema migration backlog
```
