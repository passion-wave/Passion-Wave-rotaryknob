#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_FILE="${1:-scrollwheel_JC3636K518C.yaml}"
CONFIG_BASENAME="$(basename "${CONFIG_FILE}")"
CONFIG_NAME="${CONFIG_BASENAME%.yaml}"
CONFIG_NAME_LOWER="$(printf '%s' "${CONFIG_NAME}" | tr '[:upper:]' '[:lower:]')"
CONFIG_DIR_REL="$(dirname "${CONFIG_FILE}")"
if [[ "${CONFIG_DIR_REL}" == "." ]]; then
  CONFIG_DIR_REL=""
fi
CONFIG_ABS="${REPO_ROOT}/${CONFIG_FILE}"
CONFIG_ROOT="${REPO_ROOT}${CONFIG_DIR_REL:+/${CONFIG_DIR_REL}}"
BUILD_ROOT="${CONFIG_ROOT}/.esphome"
PLATFORMIO_CACHE="${REPO_ROOT}/.esphome_cache/platformio"
ESPHOME_IMAGE="${ESPHOME_IMAGE:-ghcr.io/esphome/esphome:2026.7.0}"
detect_serial_port() {
  local candidates=()
  shopt -s nullglob
  candidates=(/dev/cu.usbmodem* /dev/cu.wchusbserial* /dev/cu.SLAB_USBtoUART*)
  shopt -u nullglob
  if [[ ${#candidates[@]} -gt 0 ]]; then
    printf '%s\n' "${candidates[0]}"
  else
    printf '%s\n' "/dev/cu.usbmodem14101"
  fi
}

SERIAL_PORT="${SERIAL_PORT:-$(detect_serial_port)}"
BAUD_RATE="${BAUD_RATE:-460800}"
CONFIG_BUILD_PATH="$(awk '/^[[:space:]]*build_path:[[:space:]]*/ {
  sub(/^[[:space:]]*build_path:[[:space:]]*/, "", $0);
  sub(/[[:space:]]+#.*$/, "", $0);
  gsub(/^[[:space:]]+|[[:space:]]+$/, "", $0);
  gsub(/^"|"$/, "", $0);
  gsub(/^'\''|'\''$/, "", $0);
  print;
  exit
}' "${CONFIG_ABS}" 2>/dev/null || true)"
if [[ -n "${CONFIG_BUILD_PATH}" ]]; then
  BUILD_DIR="${BUILD_ROOT}/${CONFIG_BUILD_PATH}"
else
  BUILD_DIR="${BUILD_ROOT}/build/${CONFIG_NAME_LOWER}"
fi
if [[ -n "${CONFIG_DIR_REL}" ]]; then
  BUILD_MOUNT="/config/${CONFIG_DIR_REL}/.esphome"
else
  BUILD_MOUNT="/config/.esphome"
fi

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
    -v "${BUILD_ROOT}:${BUILD_MOUNT}" \
    -v "${PLATFORMIO_CACHE}":/root/.platformio \
    "${ESPHOME_IMAGE}" \
    "$@"
}
