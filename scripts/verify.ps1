$ErrorActionPreference = "Stop"
.venv\Scripts\python.exe -m ruff check src tests
.venv\Scripts\python.exe -m mypy src\nhtsa_metadata
.venv\Scripts\python.exe -m pytest -q
