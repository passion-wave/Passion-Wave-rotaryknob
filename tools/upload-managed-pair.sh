#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ "${1:-}" != "--devices-awake" ]]; then
  echo "Abbruch: Beide RotaryKnobs zuerst aufwecken."
  echo "Danach erneut mit --devices-awake starten."
  exit 2
fi

required_variables=(
  PW_DEVICE_1_S3_HOST
  PW_DEVICE_1_BRIDGE_HOST
  PW_DEVICE_2_S3_HOST
  PW_DEVICE_2_BRIDGE_HOST
)

for variable_name in "${required_variables[@]}"; do
  if [[ -z "${!variable_name:-}" ]]; then
    echo "Abbruch: ${variable_name} ist nicht gesetzt."
    exit 2
  fi
done

profiles=(
  "esphome/managed-production-s3.yaml|${PW_DEVICE_1_S3_HOST}"
  "esphome/managed-production-esp32.yaml|${PW_DEVICE_1_BRIDGE_HOST}"
  "esphome/managed-test-s3.yaml|${PW_DEVICE_2_S3_HOST}"
  "esphome/managed-test-esp32.yaml|${PW_DEVICE_2_BRIDGE_HOST}"
)

for target in "${profiles[@]}"; do
  address="${target##*|}"
  if ! nc -z -w 2 "${address}" 6053; then
    echo "Abbruch vor dem ersten OTA: ${address}:6053 ist nicht erreichbar."
    exit 3
  fi
done

for target in "${profiles[@]}"; do
  config="${target%%|*}"
  address="${target##*|}"
  echo "==> OTA ${config} -> ${address}"
  # shellcheck source=esphome-common.sh
  source "${SCRIPT_DIR}/esphome-common.sh" "${config}"
  docker_esphome upload "/config/${config}" --device "${address}"
done

echo "Alle vier Managed-Endpunkte wurden aktualisiert."
