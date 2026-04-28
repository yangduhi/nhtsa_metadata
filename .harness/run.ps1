$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
& powershell -ExecutionPolicy Bypass -File (Join-Path $repoRoot "scripts\verify.ps1")
