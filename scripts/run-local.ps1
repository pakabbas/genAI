# GenAI Diagram Studio — local dev on Windows (e.g. LP-Abbas)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))

if (-not (Test-Path .venv)) {
  python -m venv .venv
}

& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

if (-not (Test-Path .env)) {
  Copy-Item .env.example .env
  Write-Host ""
  Write-Host "Created .env — set GEMINI_API_KEY in .env, then run this script again."
  exit 1
}

$env:APP_HOST = "127.0.0.1"
$env:APP_PORT = "8000"
$env:APP_ROOT_PATH = ""

Write-Host "Starting http://127.0.0.1:8000/ (Ctrl+C to stop)"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
