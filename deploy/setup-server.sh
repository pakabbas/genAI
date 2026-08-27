#!/usr/bin/env bash
# One-time server bootstrap for GenAI Creator Studio on LeadPilot GCP VM.
# Safe to re-run: idempotent nginx snippet + systemd service registration.
set -euo pipefail

APP_DIR="${APP_DIR:-/home/muhamad_abbas/apps/genAI}"
APP_USER="${APP_USER:-muhamad_abbas}"
APP_PORT="${APP_PORT:-8010}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SNIPPET_NAME="genai-leadpilot-location.conf"
NGINX_SITE="/etc/nginx/sites-enabled/leadpilotai.conf"
INCLUDE_MARKER="include snippets/${SNIPPET_NAME};"

echo "==> Ensuring app directory exists at ${APP_DIR}"
mkdir -p "${APP_DIR}"
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

echo "==> Installing nginx location snippet for /genAI/"
sudo cp "${SCRIPT_DIR}/nginx-genai-location.conf" "/etc/nginx/snippets/${SNIPPET_NAME}"

if ! sudo grep -qF "${INCLUDE_MARKER}" "${NGINX_SITE}"; then
  echo "==> Adding nginx include to ${NGINX_SITE}"
  sudo sed -i "/server_name leadpilotai.spiralloopstechnologies.com;/a\\
    ${INCLUDE_MARKER}" "${NGINX_SITE}"
else
  echo "==> Nginx include already present"
fi

echo "==> Installing systemd unit"
sudo cp "${SCRIPT_DIR}/genai.service" /etc/systemd/system/genai.service
sudo sed -i "s|__APP_DIR__|${APP_DIR}|g" /etc/systemd/system/genai.service
sudo sed -i "s|__APP_USER__|${APP_USER}|g" /etc/systemd/system/genai.service
sudo sed -i "s|__APP_PORT__|${APP_PORT}|g" /etc/systemd/system/genai.service

sudo systemctl daemon-reload
sudo systemctl enable genai.service

echo "==> Validating nginx configuration"
sudo nginx -t
sudo systemctl reload nginx

echo "==> Server bootstrap complete. Run deploy/deploy.sh to publish the app."
