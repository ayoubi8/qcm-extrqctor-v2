#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/qcm-extractor-api/current}"
SERVICE_USER="${SERVICE_USER:-qcm}"
ENV_FILE="${ENV_FILE:-/etc/qcm-extractor-api.env}"
SOURCE_DIR="$(pwd -P)"
TARGET_DIR="$(realpath -m "${APP_DIR}")"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this script with sudo from the repository root."
  exit 1
fi

if [ ! -f "app.py" ] || [ ! -f "requirements.txt" ]; then
  echo "Run this script from the repository root that contains app.py and requirements.txt."
  exit 1
fi

apt-get update
apt-get install -y python3 python3-venv python3-pip nginx git curl rsync

if ! id "${SERVICE_USER}" >/dev/null 2>&1; then
  adduser --system --group --home /opt/qcm-extractor-api "${SERVICE_USER}"
fi

mkdir -p "${APP_DIR}"
if [ "${SOURCE_DIR}" != "${TARGET_DIR}" ]; then
  rsync -a --delete \
    --exclude ".git" \
    --exclude ".venv" \
    --exclude "node_modules" \
    --exclude "apps/web/dist" \
    ./ "${APP_DIR}/"
fi
chown -R "${SERVICE_USER}:${SERVICE_USER}" /opt/qcm-extractor-api

sudo -u "${SERVICE_USER}" python3 -m venv "${APP_DIR}/.venv"
sudo -u "${SERVICE_USER}" "${APP_DIR}/.venv/bin/python" -m pip install --upgrade pip
sudo -u "${SERVICE_USER}" "${APP_DIR}/.venv/bin/python" -m pip install -r "${APP_DIR}/requirements.txt"

if [ ! -f "${ENV_FILE}" ]; then
  cp "${APP_DIR}/infra/vps/qcm-extractor-api.env.example" "${ENV_FILE}"
  chmod 600 "${ENV_FILE}"
  echo "Created ${ENV_FILE}. Edit it with your production secrets before starting the service."
fi

cp "${APP_DIR}/infra/vps/qcm-extractor-api.service" /etc/systemd/system/qcm-extractor-api.service
systemctl daemon-reload
systemctl enable qcm-extractor-api.service

echo "Deployment files installed."
echo "Next:"
echo "  1. sudo nano ${ENV_FILE}"
echo "  2. sudo systemctl restart qcm-extractor-api"
echo "  3. sudo systemctl status qcm-extractor-api"
