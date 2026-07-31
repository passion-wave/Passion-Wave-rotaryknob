#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/esphome-common.sh" "${1:-scrollwheel_JC3636K518C.yaml}"

if [[ -z "${CHIP_FAMILY:-}" ]]; then
  case "${CONFIG_NAME_LOWER}" in
    *s3*) CHIP_FAMILY="esp32s3" ;;
    *esp32*|*bridge*) CHIP_FAMILY="esp32" ;;
    *)
      echo "Chipfamilie für ${CONFIG_FILE} nicht eindeutig; CHIP_FAMILY setzen." >&2
      exit 2
      ;;
  esac
fi

if [[ ! -f "${FACTORY_BIN}" ]]; then
  echo "Firmware fehlt, starte zuerst den Build."
  echo "Erwartet: ${FACTORY_BIN}"
  exit 1
fi

if command -v esptool.py >/dev/null 2>&1; then
  ESPTOOL=(esptool.py)
elif python3 -m esptool version >/dev/null 2>&1; then
  ESPTOOL=(python3 -m esptool)
else
  echo "esptool fehlt; installiere es mit: python3 -m pip install esptool" >&2
  exit 1
fi

"${ESPTOOL[@]}" \
  --chip "${CHIP_FAMILY}" \
  --port "${SERIAL_PORT}" \
  --baud "${BAUD_RATE}" \
  --before default_reset \
  --after hard_reset \
  write_flash 0x0 "${FACTORY_BIN}"
