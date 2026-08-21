#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
script="${root}/tools/qualify-release.sh"

warmup_line="$(grep -n 'warmup_profile="esphome/managed-production-s3.yaml"' "${script}" | cut -d: -f1)"
parallel_line="$(grep -n 'remaining_profiles=(' "${script}" | cut -d: -f1)"
[[ -n "${warmup_line}" && -n "${parallel_line}" && ${warmup_line} -lt ${parallel_line} ]]

for profile in managed-production-esp32 managed-test-s3 managed-test-esp32; do
  grep -Fq "esphome/${profile}.yaml" "${script}"
done

echo "PASS cold-cache ESP-IDF warmup precedes parallel managed builds."
