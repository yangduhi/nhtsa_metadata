$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

function Resolve-VerifyPython {
    $candidates = @()

    if ($env:NHTSA_METADATA_VERIFY_PYTHON) {
        $candidates += $env:NHTSA_METADATA_VERIFY_PYTHON
    }

    $repoPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $repoPython) {
        $candidates += $repoPython
    }

    if ($env:VIRTUAL_ENV) {
        $activeVenvPython = Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"
        if (Test-Path -LiteralPath $activeVenvPython) {
            $candidates += $activeVenvPython
        }
    }

    $pathPython = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $pathPython) {
        $candidates += $pathPython.Source
    }

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            return $candidate
        }
    }

    throw "Python environment not found. Create .venv or set NHTSA_METADATA_VERIFY_PYTHON to a Python executable with ruff, mypy, pytest, and project dependencies."
}

$python = Resolve-VerifyPython
Write-Host "Using verification Python: $python"

function Invoke-VerifyStep {
    param(
        [Parameter(Mandatory = $true)]
        [string[]] $Arguments
    )

    & $python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Verification step failed: $python $($Arguments -join ' ')"
    }
}

Invoke-VerifyStep -Arguments @("-m", "ruff", "check", "src", "tests", "scripts")
Invoke-VerifyStep -Arguments @("-m", "mypy", "src\nhtsa_metadata")
Invoke-VerifyStep -Arguments @("-m", "pytest", "-q")
