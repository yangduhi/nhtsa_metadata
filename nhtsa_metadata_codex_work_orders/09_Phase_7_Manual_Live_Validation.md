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

docs/phase_reports/phase_7_manual_live_validation.md
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

`docs/phase_reports/phase_7_manual_live_validation.md`:

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
