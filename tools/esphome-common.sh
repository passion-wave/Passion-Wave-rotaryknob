#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/release-toolchain.env"
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
PLATFORMIO_CACHE="${PLATFORMIO_CACHE:-${REPO_ROOT}/.esphome_cache/platformio}"
CCACHE_CACHE="${CCACHE_CACHE:-${REPO_ROOT}/.esphome_cache/ccache}"
ESPHOME_CACHE="${ESPHOME_CACHE:-${REPO_ROOT}/.esphome}"
ESPHOME_IMAGE="${ESPHOME_IMAGE:-${ESPHOME_IMAGE_DEFAULT}}"
detect_serial_port() {
  local candidates=()
  shopt -s nullglob
  candidates=(/dev/cu.usbmodem* /dev/cu.usbserial* /dev/cu.wchusbserial* /dev/cu.SLAB_USBtoUART*)
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

mkdir -p "${BUILD_ROOT}" "${PLATFORMIO_CACHE}" "${CCACHE_CACHE}" "${ESPHOME_CACHE}"

factory_bin() {
  local found
  found="$(find "${BUILD_DIR}" -name firmware.factory.bin -print -quit 2>/dev/null || true)"
  if [[ -n "${found}" ]]; then
    printf '%s\n' "${found}"
  else
    printf '%s\n' "${BUILD_DIR}/build/firmware.factory.bin"
  fi
}

FACTORY_BIN="$(factory_bin)"

docker_esphome() {
  local esphome_args=("$@")
  set -- docker run --rm
  if [[ -n "${SOURCE_DATE_EPOCH:-}" ]]; then
    set -- "$@" -e "SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH}" \
      -v "${ESPHOME_CACHE}":/root/.cache/esphome --entrypoint python3
  fi
  if [[ -n "${CCACHE_DISABLE:-}" ]]; then
    set -- "$@" -e "CCACHE_DISABLE=${CCACHE_DISABLE}"
  else
    # ESP-IDF does not enable ccache merely because CCACHE_DIR exists.
    # PlatformIO's shared build cache complements ccache across profiles.
    set -- "$@" -e IDF_CCACHE_ENABLE=1 \
      -e PLATFORMIO_BUILD_CACHE_DIR=/root/.platformio/build-cache
  fi
  set -- "$@" \
    -v "${REPO_ROOT}":/config \
    -v "${BUILD_ROOT}:${BUILD_MOUNT}" \
    -v "${PLATFORMIO_CACHE}":/root/.platformio \
    -v "${CCACHE_CACHE}":/root/.ccache \
    -e CCACHE_DIR=/root/.ccache \
    "${ESPHOME_IMAGE}"
  if [[ -n "${SOURCE_DATE_EPOCH:-}" ]]; then
    set -- "$@" /config/tools/esphome-deterministic.py
  fi
  "$@" "${esphome_args[@]}"
}
