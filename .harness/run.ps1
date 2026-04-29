$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$requiredDocs = @(
    "docs\source_contract.md",
    "docs\source_endpoint_matrix.md",
    "docs\source_field_aliases.md",
    "docs\source_anomalies.md",
    "docs\catalog_builder_contract.md",
    "docs\filtering_contract.md",
    "docs\field_coverage_contract.md",
    "docs\db_schema_contract.md",
    "docs\operations.md"
)

foreach ($relativePath in $requiredDocs) {
    $fullPath = Join-Path $repoRoot $relativePath
    if (-not (Test-Path -LiteralPath $fullPath)) {
        throw "Missing required contract document: $relativePath"
    }
}

$envExample = Join-Path $repoRoot ".env.example"
$envText = Get-Content -LiteralPath $envExample -Raw
$requiredEnvKeys = @(
    "NHTSA_METADATA_ALLOW_LIVE=false",
    "NHTSA_METADATA_MIN_TEST_DATE=2011-01-01",
    "NHTSA_METADATA_REFERENCE_DB_PATH=D:\vscode\pulse_analysis\data\db\nhtsa_data.db"
)
foreach ($key in $requiredEnvKeys) {
    if ($envText -notmatch [regex]::Escape($key)) {
        throw ".env.example missing required setting: $key"
    }
}

$git = Get-Command git -ErrorAction SilentlyContinue
if ($null -eq $git) {
    throw "git is required for harness preflight"
}

& git -C $repoRoot check-ignore -q "data/stratified_live_pilot_2011plus.sqlite"
if ($LASTEXITCODE -ne 0) {
    throw "data pilot SQLite outputs must be ignored by git"
}

& git -C $repoRoot check-ignore -q "data/stratified_live_pilot_2011plus_manifest.csv"
if ($LASTEXITCODE -ne 0) {
    throw "data pilot manifest outputs must be ignored by git"
}

& powershell -ExecutionPolicy Bypass -File (Join-Path $repoRoot "scripts\verify.ps1")
