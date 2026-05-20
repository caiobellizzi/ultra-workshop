#!/usr/bin/env bash
# install.sh — Idempotent VPS installer for ultra-workshop Hermes service
# Usage: bash scripts/install.sh [--dry-run]
# Requires: SSH access to root@31.97.130.253

set -euo pipefail

VPS="root@31.97.130.253"
INSTALL_DIR="/opt/ultra-workshop"
HERMES_INSTALL_DIR="${INSTALL_DIR}/hermes"
LOG_DIR="/var/log/ultra-workshop"
UNIT_FILE="deploy/systemd/uws-hermes.service"
CONFIG_DIR="hermes-config"
DRY_RUN=false

for arg in "$@"; do
  [[ "$arg" == "--dry-run" ]] && DRY_RUN=true
done

rsh() {
  if $DRY_RUN; then
    echo "[dry-run] ssh ${VPS}: $*"
  else
    ssh "$VPS" "$@"
  fi
}

rsync_files() {
  local src="$1" dst="$2"
  if $DRY_RUN; then
    echo "[dry-run] rsync -av $src ${VPS}:${dst}"
  else
    rsync -av "$src" "${VPS}:${dst}"
  fi
}

echo "==> Step 1: GUARD — check SSH reachability"
if ! $DRY_RUN; then
  ssh -o ConnectTimeout=10 "$VPS" "echo reachable" || {
    echo "ERROR: Cannot reach $VPS via SSH" >&2; exit 1
  }
fi

echo "==> Step 2: uws USER"
rsh "id uws 2>/dev/null && echo 'uws exists — skip' || useradd --system --home-dir /home/uws --create-home --shell /bin/bash uws"

echo "==> Step 3: DIRS"
rsh "mkdir -p ${INSTALL_DIR}/{hermes,hermes-config,deploy/systemd} ${LOG_DIR} && \
  chown -R uws:uws ${INSTALL_DIR} ${LOG_DIR} && \
  mkdir -p /home/uws/.hermes && \
  chown -R uws:uws /home/uws"

echo "==> Step 4: HERMES INSTALL (as uws)"
rsh "if [ -f '${HERMES_INSTALL_DIR}/hermes-agent/.venv/bin/hermes' ]; then
  echo 'Hermes already installed — skip'
else
  echo 'Installing Hermes...'
  # Load nvm and install hermes using the official installer
  export HOME=/home/uws
  sudo -u uws bash -c '
    export HOME=/home/uws
    export NVM_DIR=\"/home/uws/.nvm\"
    [ -s \"\${NVM_DIR}/nvm.sh\" ] && . \"\${NVM_DIR}/nvm.sh\"
    export HERMES_INSTALL_DIR=${HERMES_INSTALL_DIR}
    curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | HERMES_INSTALL_DIR=${HERMES_INSTALL_DIR} bash
  '
fi"

echo "==> Step 5: CONFIG DEPLOY"
rsync_files "${CONFIG_DIR}/" "${INSTALL_DIR}/hermes-config/"
rsh "chown -R uws:uws ${INSTALL_DIR}/hermes-config/"
# Symlink fallback: if HERMES_CONFIG_PATH is not honored, symlink into ~/.hermes/
rsh "mkdir -p /home/uws/.hermes && \
  if [ ! -f '/home/uws/.hermes/config.yaml' ] || [ -L '/home/uws/.hermes/config.yaml' ]; then
    sudo -u uws ln -sf ${INSTALL_DIR}/hermes-config/config.yaml /home/uws/.hermes/config.yaml && \
    echo 'symlink created'
  else
    echo 'config.yaml is a regular file — leaving in place'
  fi"

echo "==> Step 6: UNIT FILE"
if ! $DRY_RUN; then
  scp "${UNIT_FILE}" "${VPS}:/etc/systemd/system/uws-hermes.service"
fi
rsh "systemctl daemon-reload && systemctl enable uws-hermes"

echo "==> Step 7: START"
rsh "systemctl start uws-hermes"

echo "==> Step 8: VERIFY"
rsh "sleep 5 && systemctl is-active uws-hermes"

echo "==> Done."
