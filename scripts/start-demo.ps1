$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
        if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
            throw 'Install uv or create a Python 3.12 .venv first; see README.md.'
        }
        uv venv --python 3.12 .venv
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the local environment.' }
    }
    & .venv/Scripts/python.exe -c 'import moto, boto3'
    if ($LASTEXITCODE -ne 0) {
        & .venv/Scripts/python.exe -m ensurepip
        & .venv/Scripts/python.exe -m pip install -r tests/requirements.txt -r policy_assistant/requirements.txt
        if ($LASTEXITCODE -ne 0) { throw 'Could not install local demo dependencies.' }
    }
    & .venv/Scripts/python.exe -B -m scripts.demo_server
} finally { Pop-Location }
