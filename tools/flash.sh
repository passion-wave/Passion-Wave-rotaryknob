#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/esphome-common.sh" "${1:-scrollwheel_JC3636K518C.yaml}"

if [[ ! -f "${FACTORY_BIN}" ]]; then
  echo "Firmware fehlt, starte zuerst den Build."
  echo "Erwartet: ${FACTORY_BIN}"
  exit 1
fi

esptool.py \
  --chip esp32s3 \
  --port "${SERIAL_PORT}" \
  --baud "${BAUD_RATE}" \
  --before default_reset \
  --after hard_reset \
  write_flash 0x0 "${FACTORY_BIN}"
