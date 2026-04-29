# nhtsa_metadata Agent Instructions

항상 한국어로 답변하되, 사용자가 영어를 요청하면 영어로 전환한다.

## Project Guardrails

- 이 프로젝트는 2011년 이후 NHTSA crash test metadata-only catalog DB다.
- canonical/read-model 대상은 `test_date >= 2011-01-01`로 제한한다.
- `modelYear`는 scope 판단 기준이 아니다.
- `test_date` missing 또는 parse 실패 record는 canonical/read-model에서 제외한다.
- 다운로드 실행, waveform 분석, UI, full crawler는 현재 범위가 아니다.
- 기본 `pytest`, `scripts/verify.ps1`, `.harness/run.ps1`에서 live NHTSA API 호출은 금지한다.
- live API는 manual validation 명령에서 `--source live`, `--allow-live`, `NHTSA_METADATA_ALLOW_LIVE=true`가 모두 있을 때만 허용한다.
- `D:\vscode\pulse_analysis\data\db\nhtsa_data.db`는 bounded manifest seed reference로만 사용하고 source of truth로 승격하지 않는다.
- 기존 `nhtsa_gui` / `nhtsa` 경로는 read-only reference로만 사용한다.
- `.git`, `.venv`, DB, `data/manual`, cache, screenshots, response dumps는 복사하거나 커밋하지 않는다.

## Engineering Rules

- 최소 범위, 최소 diff 원칙을 따른다.
- source payload는 버리지 않고 raw/provenance 계층에 보존한다.
- canonical/read-model은 raw payload에서 rebuild 가능한 파생물로 유지한다.
- `0`, `"0"`, `null`, missing, empty string은 구분한다.
- 구현 단계별로 phase report와 검증 결과를 남긴다.
- 100건 확장 전에는 `.skills/nhtsa-metadata-verify`, `.skills/nhtsa-metadata-live-pilot`, `.skills/nhtsa-metadata-scope-audit` 절차를 우선 확인한다.
