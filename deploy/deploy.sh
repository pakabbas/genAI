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
cat > .env <<EOF
GEMINI_API_KEY=${GEMINI_API_KEY:?GEMINI_API_KEY is required}
GEMINI_MODEL=${GEMINI_MODEL:-gemini-flash-lite-latest}
APP_HOST=127.0.0.1
APP_PORT=${APP_PORT}
APP_ROOT_PATH=${APP_ROOT_PATH}
EOF
chmod 600 .env

echo "==> Restarting genai.service"
sudo systemctl restart genai.service
sleep 2

echo "==> Health check (local)"
curl -fsS "http://127.0.0.1:${APP_PORT}/api/health" | tee /tmp/genai-health.json
echo
echo "==> Deploy finished successfully"
