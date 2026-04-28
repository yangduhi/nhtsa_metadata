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
├── README.md
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
├── docs\operations.md
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

## `README.md`

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

`docs/phase_reports/phase_0_scaffold.md` 생성:

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
