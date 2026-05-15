#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/esphome-common.sh" "${1:-scrollwheel_JC3636K518C.yaml}"

docker_esphome config "/config/${CONFIG_FILE}"
