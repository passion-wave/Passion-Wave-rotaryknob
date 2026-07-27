#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${1:-esphome/managed-production-s3.yaml}"
if [[ $# -gt 0 && "${1}" == *.yaml ]]; then
  CONFIG_FILE="$1"
  shift
fi

source "${SCRIPT_DIR}/esphome-common.sh" "${CONFIG_FILE}"

echo "==> ESPHome logs: ${CONFIG_FILE}"
echo "==> Tipp: Debug per HA-Service einschalten: esphome.passion_wave_rotaryknob_media_debug_on"
docker_esphome logs "/config/${CONFIG_FILE}" "$@"
