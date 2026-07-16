#!/usr/bin/env bash
set -euo pipefail

APP_SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_DIR=/opt/solar-metadata-tagger
CONFIG_DIR=/etc/solar-tagger
DATA_DIR=/opt/ssd/sunnybotics
SERVICE_USER=solarbot

if [[ ${EUID} -ne 0 ]]; then
  echo "Run this installer with sudo." >&2
  exit 1
fi

if [[ ! -d /opt/ssd ]]; then
  echo "/opt/ssd does not exist. Mount the WD Blue NVMe before installation." >&2
  exit 1
fi
if ! mountpoint -q /opt/ssd; then
  echo "Warning: /opt/ssd is not currently a mount point. The systemd service will refuse to start until it is mounted." >&2
fi

if ! id "${SERVICE_USER}" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir /var/lib/solarbot --shell /usr/sbin/nologin "${SERVICE_USER}"
fi
usermod -a -G dialout "${SERVICE_USER}"

install -d -m 0755 "${APP_DIR}" "${CONFIG_DIR}"
install -d -o "${SERVICE_USER}" -g "${SERVICE_USER}" -m 0750 "${DATA_DIR}"

# Copy source without runtime/test artifacts; tar is available on standard Ubuntu images.
find "${APP_DIR}" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
tar -C "${APP_SOURCE}" \
  --exclude='.venv' --exclude='__pycache__' --exclude='.pytest_cache' --exclude='runtime-data*' \
  -cf - . | tar -C "${APP_DIR}" -xf -

python3 -m venv "${APP_DIR}/.venv"
"${APP_DIR}/.venv/bin/python" -m pip install --upgrade pip
"${APP_DIR}/.venv/bin/python" -m pip install "${APP_DIR}"

if [[ ! -f "${CONFIG_DIR}/config.json" ]]; then
  install -m 0640 -o root -g "${SERVICE_USER}" \
    "${APP_DIR}/config/rubik_pi_lucid_config.json" "${CONFIG_DIR}/config.json"
  echo "Installed template configuration at ${CONFIG_DIR}/config.json; edit it before enabling the service."
fi
if [[ ! -f "${CONFIG_DIR}/site-layout.geojson" ]]; then
  install -m 0640 -o root -g "${SERVICE_USER}" \
    "${APP_DIR}/config/example_layout.geojson" "${CONFIG_DIR}/site-layout.geojson"
  echo "Installed EXAMPLE layout. Replace it with surveyed coordinates before field use."
fi

install -m 0644 "${APP_DIR}/deploy/systemd/solar-capture.service" /etc/systemd/system/solar-capture.service
chown -R root:root "${APP_DIR}"
chmod -R a+rX "${APP_DIR}"
systemctl daemon-reload

cat <<EOF
Installation complete.

Required before start:
  1. Mount the WD Blue NVMe at /opt/ssd and add it to /etc/fstab by UUID.
  2. Install LUCID Arena SDK for ARM64 Ubuntu and make arena_api available to ${APP_DIR}/.venv.
  3. Edit ${CONFIG_DIR}/config.json (mission ID and camera serial).
  4. Replace ${CONFIG_DIR}/site-layout.geojson with surveyed panel polygons.
  5. Run the preflight commands in docs/OPERATIONS.md.

Then enable:
  systemctl enable --now solar-capture.service
EOF
