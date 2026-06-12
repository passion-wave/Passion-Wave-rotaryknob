#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${1:-esphome/passion-wave-rotaryknob.yaml}"

echo "==> Build: ${CONFIG_FILE}"
"${SCRIPT_DIR}/build.sh" "${CONFIG_FILE}"

echo
echo "==> Flash: ${CONFIG_FILE}"
"${SCRIPT_DIR}/flash.sh" "${CONFIG_FILE}"

echo
echo "Done: build and flash completed."
