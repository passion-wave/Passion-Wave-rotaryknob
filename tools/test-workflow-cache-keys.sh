#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
workflows=(quality.yml public-firmware.yml rc-reproducibility.yml)

for name in "${workflows[@]}"; do
  file="${root}/.github/workflows/${name}"
  grep -Fq 'id: firmware-inputs' "${file}"
  grep -Fq '${{ steps.firmware-inputs.outputs.hash }}' "${file}"
  grep -Fq 'linux-amd64-a018bf33' "${file}"
  if grep -Fq "hashFiles('esphome/**'" "${file}"; then
    echo "Generated ESPHome trees must not be hashed in ${name}" >&2
    exit 1
  fi
done

for name in quality.yml public-firmware.yml; do
  if grep -Fq '            esphome/.esphome' "${root}/.github/workflows/${name}"; then
    echo "Generated build trees must not be cached in ${name}" >&2
    exit 1
  fi
done

echo "PASS workflow cache keys use the tracked pre-build source fingerprint."
