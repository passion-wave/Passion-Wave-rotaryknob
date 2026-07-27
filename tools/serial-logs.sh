#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${1:-esphome/managed-production-s3.yaml}"
if [[ $# -gt 0 && "${1}" == *.yaml ]]; then
  CONFIG_FILE="$1"
  shift
fi

source "${SCRIPT_DIR}/esphome-common.sh" "${CONFIG_FILE}"

LOG_BAUD_RATE="${LOG_BAUD_RATE:-115200}"

echo "==> Serial logs: ${SERIAL_PORT} @ ${LOG_BAUD_RATE}"
echo "==> Beenden in screen: Ctrl-A, dann K, dann y"
exec screen "${SERIAL_PORT}" "${LOG_BAUD_RATE}"
