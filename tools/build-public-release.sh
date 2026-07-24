#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output_dir="${1:-${repo_dir}/release/public}"
esphome_command="${ESPHOME_COMMAND:-esphome}"

mkdir -p "${output_dir}/s3" "${output_dir}/esp32"

"${esphome_command}" compile "${repo_dir}/esphome/factory-s3.yaml"
"${esphome_command}" compile "${repo_dir}/esphome/factory-esp32.yaml"

cp "${repo_dir}/esphome/.esphome/build/passion_wave_factory_s3/build/firmware.factory.bin" \
  "${output_dir}/s3/passion-wave-rotaryknob-s3.factory.bin"
cp "${repo_dir}/esphome/.esphome/build/passion_wave_factory_esp32/build/firmware.factory.bin" \
  "${output_dir}/esp32/passion-wave-rotaryknob-esp32.factory.bin"

(
  cd "${output_dir}"
  shasum -a 256 \
    s3/passion-wave-rotaryknob-s3.factory.bin \
    esp32/passion-wave-rotaryknob-esp32.factory.bin > SHA256SUMS
)

echo "Public release artifacts: ${output_dir}"
