param(
    [switch]$AllowLive,
    [string]$DatabaseUrl = "sqlite:///data/live_validation.sqlite"
)

$ErrorActionPreference = "Stop"

if (-not $AllowLive) {
    throw "Manual live validation requires -AllowLive."
}

$env:NHTSA_METADATA_ALLOW_LIVE = "true"

.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog collect `
    --manifest tests\fixtures\live_sample_manifest.csv `
    --database-url $DatabaseUrl `
    --source live `
    --allow-live

.venv\Scripts\python.exe -m nhtsa_metadata.cli coverage report --database-url $DatabaseUrl
.venv\Scripts\python.exe -m nhtsa_metadata.cli catalog assert-live-baseline --database-url $DatabaseUrl
