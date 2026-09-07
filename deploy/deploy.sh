#!/usr/bin/env bash
# Deploy or update GenAI Creator Studio on the GCP VM.
set -euo pipefail

APP_DIR="${APP_DIR:-/home/muhamad_abbas/apps/genAI}"
APP_PORT="${APP_PORT:-8010}"
APP_ROOT_PATH="${APP_ROOT_PATH:-/genAI}"

cd "${APP_DIR}"

echo "==> Creating virtualenv (if needed)"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

echo "==> Installing Python dependencies"
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo "==> Writing runtime .env"
if [[ -z "${DB_PASSWORD:-}" && -f /opt/leadpilot/config/mysqldb.txt ]]; then
  DB_HOST="${DB_HOST:-$(awk -F': ' '/^host:/{print $2}' /opt/leadpilot/config/mysqldb.txt | tr -d '\r')}"
  DB_NAME="${DB_NAME:-$(awk -F': ' '/^db:/{print $2}' /opt/leadpilot/config/mysqldb.txt | tr -d '\r')}"
  DB_USER="${DB_USER:-$(awk -F': ' '/^user:/{print $2}' /opt/leadpilot/config/mysqldb.txt | tr -d '\r')}"
  DB_PASSWORD="$(awk -F': ' '/^password:/{print $2}' /opt/leadpilot/config/mysqldb.txt | tr -d '\r')"
fi
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-3306}"
DB_NAME="${DB_NAME:-leadpilot}"
DB_USER="${DB_USER:-leadpilot}"
if [[ -z "${DB_PASSWORD:-}" ]]; then
  echo "ERROR: DB_PASSWORD is required (env or /opt/leadpilot/config/mysqldb.txt)" >&2
  exit 1
fi
cat > .env <<EOF
GEMINI_API_KEY=${GEMINI_API_KEY:?GEMINI_API_KEY is required}
GEMINI_MODEL=${GEMINI_MODEL:-gemini-flash-lite-latest}
APP_HOST=127.0.0.1
APP_PORT=${APP_PORT}
APP_ROOT_PATH=${APP_ROOT_PATH}
DB_HOST=${DB_HOST:-127.0.0.1}
DB_PORT=${DB_PORT:-3306}
DB_NAME=${DB_NAME:-leadpilot}
DB_USER=${DB_USER:-leadpilot}
DB_PASSWORD=${DB_PASSWORD:?DB_PASSWORD is required}
EOF
chmod 600 .env

echo "==> Restarting genai.service"
sudo systemctl restart genai.service
sleep 2

echo "==> Health check (local)"
curl -fsS "http://127.0.0.1:${APP_PORT}/api/health" | tee /tmp/genai-health.json
echo
echo "==> Deploy finished successfully"
