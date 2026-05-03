# 작업지시서: 100건 bounded 2011+ pilot manifest 설계 및 판정표 작성

## 0. 현재 판정

semantic cardinality remediation은 통과한 상태로 본다.

다음 단계는 100건 bounded 2011+ pilot의 **설계와 manifest 후보 생성 계획**이다.  
이 작업지시서는 live collect 실행 지시가 아니다.

## 1. 범위

### 포함

- 2011년 이후 테스트만 대상으로 한다.
- 기준은 `test_date >= 2011-01-01`이다.
- `modelYear` 또는 `test_no` range는 scope 기준으로 사용하지 않는다.
- 40건 2011+ pilot에서 검증된 semantic audit 기준을 100건 pilot에도 그대로 적용한다.
- 10001, 10003, 7201은 baseline/anchor로 포함한다.

### 제외

- full crawler 구현 또는 실행
- 100건 live collect 실행
- 250건 pilot 실행
- 파일 다운로드
- waveform, TDMS, UDS, ABF, ISO, EV package 내용 분석
- 기본 `verify.ps1` 또는 `.harness/run.ps1`에 live API 호출 추가
- `data/` 산출물 commit

## 2. 목표 산출물

Codex는 우선 다음 문서와 후보 산출물 계획만 만든다.

```text
docs/phase_reports/2026-04-30__100-test-pilot__pass__100test-2011plus-manifest-plan.md
docs/phase_reports/2026-04-30__100-test-pilot__pass__100test-2011plus-acceptance-matrix.md
```

선택적으로, live 호출 없이 local reference DB만 사용해 후보 manifest를 만들 수 있다면 다음 파일을 생성할 수 있다. 단, 이 파일은 `data/` 아래에 두고 commit하지 않는다.

```text
data/stratified_live_pilot_2011plus_100_manifest_candidate.csv
```

## 3. 사전 조건

현재 상태는 다음이어야 한다.

```text
branch: main
HEAD: e2eb298 또는 그 이후 main commit
working tree: clean
pytest: pass
ruff: pass
mypy: pass
scripts/verify.ps1: pass
.harness/run.ps1: pass
```

확인 명령:

```powershell
git status --short
git rev-parse --short HEAD
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check src tests
.venv\Scripts\python.exe -m mypy src\nhtsa_metadata
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
powershell -ExecutionPolicy Bypass -File .harness\run.ps1
```

## 4. 100건 manifest 설계 원칙

### 4.1 Scope gate

모든 candidate row는 다음 조건을 만족해야 한다.

```text
test_date >= 2011-01-01
test_date_parse_status = parsed
scope_status = in_scope
```

다음 row는 manifest 후보에서 제외한다.

```text
test_date < 2011-01-01
test_date missing
test_date parse failed
```

### 4.2 Anchor tests

다음 anchor는 반드시 포함한다.

```text
7201  - 확인된 2011+ earliest seed, 2011-01-03
10001 - modern frontal barrier baseline
10003 - modern side impactor / impactor-as-vehicle baseline
```

### 4.3 Stratification

100건은 단순 test_no 순서로 뽑지 않는다.

우선 stratification 기준:

```text
1. normalized test_configuration
2. test_family / classification
3. year bucket
4. media/data_package presence
5. occupant/restraint presence
6. instrumentation volume tier
```

권장 year bucket:

```text
2011-2012
2013-2014
2015-2016
2017-2018
2019-2020
2021-2022
2023+
```

`--max-per-configuration`만으로는 100건 도달을 막을 수 있으므로 다음 중 하나를 선택한다.

권장 A:

```text
--limit 100
--max-per-configuration 20
```

권장 B:

```text
configuration 단독 cap 대신
(configuration, year_bucket) 또는 (configuration, test_family) combined stratum cap 사용
```

CLI가 combined stratum cap을 아직 지원하지 않으면, 문서에 gap으로 기록하고 100건 pilot 전 보강 여부를 판단한다.

## 5. Reference DB seed와 live by-search 차이 문서화

`--reference-database`는 canonical source가 아니다. bounded manifest seed일 뿐이다.

`docs/phase_reports/2026-04-30__100-test-pilot__pass__100test-2011plus-manifest-plan.md`에 다음을 기록한다.

```text
reference DB path
reference DB crash_tests count
parseable date count
2011+ parseable count
pre-2011 parseable count
missing/parse failed count
candidate manifest generation rules
known limitation: reference DB is not canonical source
live by-search validation requirement
```

다음 discrepancy table을 준비한다.

```text
field
reference_value
live_value
status
resolution
```

비교 대상:

```text
test_no
test_date
test_configuration
test_type
model_year
vehicle make/model when available
```

## 6. 후보 manifest CSV schema

100건 후보 manifest는 최소 다음 column을 갖는다.

```text
test_no
test_date
year_bucket
test_configuration_key
test_configuration
test_family
classification_status
reason
scope_status
seed_source
anchor_flag
```

권장 추가 column:

```text
expected_endpoint_risk
expected_media_presence
expected_data_package_presence
expected_restraint_presence
expected_occupant_presence
expected_instrumentation_tier
```

## 7. 100건 pilot acceptance matrix

`docs/phase_reports/2026-04-30__100-test-pilot__pass__100test-2011plus-acceptance-matrix.md`에 아래 판정표를 작성한다.

### 7.1 Manifest acceptance

```text
manifest rows = 100
all rows test_date >= 2011-01-01
all rows scope_status = in_scope
10001 included
10003 included
7201 included
max normalized configuration bucket <= configured cap
no duplicate test_no
no missing test_date
no parse failed test_date
```

### 7.2 Collection acceptance, live 실행 후 판정용

```text
collection run items = 100
failed collection items = 0 또는 documented allowed transient only
source_payloads > 0
source_payload_observations > 0
all source payloads associated with endpoint_name
all expected paginated instrumentation pages collected
allowed empty endpoints not treated as failure
```

### 7.3 Scope audit acceptance

```text
scope violations = 0
read-model out-of-scope rows = 0
missing canonical test_date = 0
date parse failure canonical rows = 0
canonical tests = 100
test_filter_summary = 100
```

### 7.4 Duplicate and semantic audit acceptance

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

Semantic hard failures must be 0.

Required semantic checks:

```text
occupants are normalized occupant slots
restraints preserve occupant context
occupant-specific restraint context loss = 0
barrier semantic status not investigate for baseline tests
restraint_info expected/actual payloads match
restraint_info missing requests = 0
```

### 7.5 Baseline acceptance

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

### 7.6 Asset acceptance

```text
data_package candidates = classified_data_packages
unclassified_asset_candidates = 0
files are not downloaded
asset registry stores URL/metadata only
```

### 7.7 Field coverage acceptance

```text
field path wildcard normalization present, e.g. $.results[*].axisDirofSensor
unmapped field count reported
new unmapped critical fields identified
no mapped field regression
```

### 7.8 Safety acceptance

```text
full crawler not executed
file download not executed
waveform/package parsing not executed
basic verify/harness fixture-only
--allow-live missing fails
NHTSA_METADATA_ALLOW_LIVE missing fails
failed safety command creates no output manifest
working tree clean
data artifacts ignored
```

## 8. Optional candidate manifest generation without live collect

If local reference DB candidate generation is supported, produce a candidate manifest without running live collect.

Example candidate generation command, adjust to actual CLI behavior:

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog build-manifest `
  --source reference `
  --reference-database D:\vscode\pulse_analysis\data\db\nhtsa_data.db `
  --output data\stratified_live_pilot_2011plus_100_manifest_candidate.csv `
  --limit 100 `
  --max-per-configuration 20 `
  --min-test-date 2011-01-01
```

If CLI does not support `--source reference`, do not invent behavior. Instead document the exact current supported command and whether it would call live APIs.

## 9. Live commands to prepare but not execute

The following commands may be documented for later approval. Do not execute them in this planning task.

### 9.1 Live manifest build, approval required

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

### 9.2 Live collect, separate approval required

```powershell
powershell -ExecutionPolicy Bypass -File scripts\live_pilot_validate.ps1 `
  -AllowLive `
  -DatabaseUrl sqlite:///data/stratified_live_pilot_2011plus_100.sqlite `
  -Manifest data/stratified_live_pilot_2011plus_100_manifest.csv
```

### 9.3 Schema audit after live collect

```powershell
.venv\Scripts\python.exe -m nhtsa_metadata.cli schema audit `
  --database-url sqlite:///data/stratified_live_pilot_2011plus_100.sqlite `
  --output data/schema_audit_report_2011plus_100.json `
  --include-duplicate-details `
  --duplicate-detail-limit 50
```

## 10. Planning task completion criteria

This planning task is complete when:

```text
- 100test_2011plus_manifest_plan.md exists
- 100test_2011plus_acceptance_matrix.md exists
- no live collect was executed
- no full crawler was executed
- no files were downloaded
- basic verification passes
- working tree clean after intended docs commit
- data candidate artifacts, if any, remain ignored
```

## 11. Report format

Codex should report:

```text
결론:
- 100건 bounded 2011+ pilot 계획 통과 / 부분 통과 / 실패
- live manifest build 실행 여부
- live collect 실행 여부
- full crawler 실행 여부
- 파일 다운로드 여부

설계 산출물:
- manifest plan 문서 경로
- acceptance matrix 문서 경로
- candidate manifest path, if generated

Manifest design:
- limit
- min_test_date
- baseline anchors
- stratification dimensions
- max-per-configuration or combined stratum policy
- reference DB usage policy

Acceptance criteria:
- scope
- duplicate
- semantic cardinality
- baseline
- asset/data package
- restraint scheduling
- safety

검증:
- pytest
- ruff
- mypy
- verify
- harness

Git:
- branch
- commit
- status
- push 여부

후속:
- live manifest build 승인 필요 여부
- live collect 승인 필요 여부
```
