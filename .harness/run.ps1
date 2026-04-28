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
    "docs\db_schema_contract.md"
)

foreach ($relativePath in $requiredDocs) {
    $fullPath = Join-Path $repoRoot $relativePath
    if (-not (Test-Path $fullPath)) {
        throw "Missing required contract document: $relativePath"
    }
}

& powershell -ExecutionPolicy Bypass -File (Join-Path $repoRoot "scripts\verify.ps1")
