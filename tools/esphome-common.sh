#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_FILE="${1:-scrollwheel_JC3636K518C.yaml}"
CONFIG_BASENAME="$(basename "${CONFIG_FILE}")"
CONFIG_NAME="${CONFIG_BASENAME%.yaml}"
CONFIG_NAME_LOWER="$(printf '%s' "${CONFIG_NAME}" | tr '[:upper:]' '[:lower:]')"
BUILD_ROOT="${REPO_ROOT}/.esphome"
PLATFORMIO_CACHE="${REPO_ROOT}/.esphome_cache/platformio"
ESPHOME_IMAGE="${ESPHOME_IMAGE:-ghcr.io/esphome/esphome:2026.2.2}"
SERIAL_PORT="${SERIAL_PORT:-/dev/cu.usbmodem14101}"
BAUD_RATE="${BAUD_RATE:-460800}"
BUILD_DIR="${BUILD_ROOT}/build/${CONFIG_NAME_LOWER}"

mkdir -p "${BUILD_ROOT}" "${PLATFORMIO_CACHE}"

factory_bin() {
  local found
  found="$(find "${BUILD_DIR}/.pioenvs" -mindepth 2 -maxdepth 2 -name firmware.factory.bin -print -quit 2>/dev/null || true)"
  if [[ -n "${found}" ]]; then
    printf '%s\n' "${found}"
  else
    printf '%s\n' "${BUILD_DIR}/.pioenvs/${CONFIG_NAME_LOWER}/firmware.factory.bin"
  fi
}

FACTORY_BIN="$(factory_bin)"

docker_esphome() {
  docker run --rm \
    -v "${REPO_ROOT}":/config \
    -v "${BUILD_ROOT}":/config/.esphome \
    -v "${PLATFORMIO_CACHE}":/root/.platformio \
    "${ESPHOME_IMAGE}" \
    "$@"
}
