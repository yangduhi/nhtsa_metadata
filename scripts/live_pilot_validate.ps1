param(
    [switch]$AllowLive,
    [string]$DatabaseUrl = "sqlite:///data/stratified_live_pilot_2011plus.sqlite",
    [string]$Manifest = "data/stratified_live_pilot_2011plus_manifest.csv",
    [string]$AuditOutput = "data/schema_audit_report_2011plus.json"
)

$ErrorActionPreference = "Stop"

if (-not $AllowLive) {
    throw "Live pilot validation requires -AllowLive."
}

if (-not (Test-Path -LiteralPath $Manifest)) {
    throw "Manifest not found: $Manifest"
}

$env:NHTSA_METADATA_ALLOW_LIVE = "true"

.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog collect `
    --manifest $Manifest `
    --database-url $DatabaseUrl `
    --source live `
    --allow-live

.venv\Scripts\python.exe -m nhtsa_metadata.cli coverage report --database-url $DatabaseUrl
.venv\Scripts\python.exe -m nhtsa_metadata.cli schema audit `
    --database-url $DatabaseUrl `
    --output $AuditOutput `
    --include-duplicate-details
.venv\Scripts\python.exe -m nhtsa_metadata.cli scale report --database-url $DatabaseUrl

$env:NHTSA_METADATA_PILOT_DB_URL = $DatabaseUrl
@'
import json
import os

from fastapi.testclient import TestClient

from nhtsa_metadata.api.app import create_app
from nhtsa_metadata.config import Settings

settings = Settings(database_url=os.environ["NHTSA_METADATA_PILOT_DB_URL"], environment="test")
client = TestClient(create_app(settings))
paths = [
    "/api/health",
    "/api/tests",
    "/api/tests/10001",
    "/api/tests/10003",
    "/api/filter-options",
    "/api/coverage/fields",
]
result = {}
for path in paths:
    response = client.get(path)
    body = response.json()
    result[path] = {
        "status_code": response.status_code,
        "count": body.get("count") if isinstance(body, dict) else None,
        "found": body.get("found") if isinstance(body, dict) else None,
    }
    if response.status_code != 200:
        raise SystemExit(json.dumps(result, sort_keys=True))
print(json.dumps(result, sort_keys=True))
'@ | .venv\Scripts\python.exe -
