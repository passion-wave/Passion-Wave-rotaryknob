#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output_dir="${1:-${repo_dir}/release/public}"
version="$(tr -d '[:space:]' < "${repo_dir}/VERSION")"
resolved_dir="$(mktemp -d)"

cleanup() {
  rm -f "${resolved_dir}/factory-s3.yaml" "${resolved_dir}/factory-esp32.yaml"
  rmdir "${resolved_dir}"
}
trap cleanup EXIT

require_line() {
  local pattern="$1"
  local file="$2"
  local description="$3"

  if ! grep -q "${pattern}" "${file}"; then
    echo "Public factory validation failed: ${description}." >&2
    exit 1
  fi
}

mkdir -p "${output_dir}/s3" "${output_dir}/esp32"

if [[ -n "${ESPHOME_COMMAND:-}" ]]; then
  "${ESPHOME_COMMAND}" config "${repo_dir}/esphome/factory-s3.yaml" \
    > "${resolved_dir}/factory-s3.yaml"
  "${ESPHOME_COMMAND}" config "${repo_dir}/esphome/factory-esp32.yaml" \
    > "${resolved_dir}/factory-esp32.yaml"
  "${ESPHOME_COMMAND}" compile "${repo_dir}/esphome/factory-s3.yaml"
  "${ESPHOME_COMMAND}" compile "${repo_dir}/esphome/factory-esp32.yaml"
else
  docker run --rm -v "${repo_dir}":/config \
    "${ESPHOME_IMAGE:-ghcr.io/esphome/esphome:2026.7.0}" \
    config /config/esphome/factory-s3.yaml \
    > "${resolved_dir}/factory-s3.yaml"
  docker run --rm -v "${repo_dir}":/config \
    "${ESPHOME_IMAGE:-ghcr.io/esphome/esphome:2026.7.0}" \
    config /config/esphome/factory-esp32.yaml \
    > "${resolved_dir}/factory-esp32.yaml"
  "${repo_dir}/tools/build.sh" esphome/factory-s3.yaml
  "${repo_dir}/tools/build.sh" esphome/factory-esp32.yaml
fi

for resolved_config in \
    "${resolved_dir}/factory-s3.yaml" "${resolved_dir}/factory-esp32.yaml"; do
  if ! awk '
    /^api:$/ { in_api = 1; next }
    in_api && /^[^[:space:]]/ { exit }
    in_api && /^  encryption: \{\}$/ { found = 1 }
    END { exit !found }
  ' "${resolved_config}"; then
    echo "Public factory API must enable runtime encryption without a compiled key: ${resolved_config}" >&2
    exit 1
  fi
  if ! grep -A1 '^provisioning:$' "${resolved_config}" \
      | grep -q '^  timeout: 20min$'; then
    echo "Public factory provisioning window must be 20min: ${resolved_config}" >&2
    exit 1
  fi
done

require_line 'friendly_name: PassionWave Rotaryknob$' \
  "${resolved_dir}/factory-s3.yaml" "S3 friendly name is missing"
require_line 'friendly_name: PassionWave Rotaryknob Bridge$' \
  "${resolved_dir}/factory-esp32.yaml" "ESP32 bridge friendly name is missing"
require_line 'name_add_mac_suffix: true' \
  "${resolved_dir}/factory-s3.yaml" "S3 MAC suffix is disabled"
require_line 'name_add_mac_suffix: true' \
  "${resolved_dir}/factory-esp32.yaml" "ESP32 bridge MAC suffix is disabled"
require_line '^improv_serial:' \
  "${resolved_dir}/factory-s3.yaml" "S3 Improv Serial is disabled"
require_line '^improv_serial:' \
  "${resolved_dir}/factory-esp32.yaml" "ESP32 bridge Improv Serial is disabled"
require_line '^  baud_rate: 115200$' \
  "${resolved_dir}/factory-s3.yaml" "S3 logger does not use 115200 baud"
require_line '^  baud_rate: 115200$' \
  "${resolved_dir}/factory-esp32.yaml" "ESP32 bridge logger does not use 115200 baud"
require_line '^  hardware_uart: USB_SERIAL_JTAG$' \
  "${resolved_dir}/factory-s3.yaml" "S3 Improv transport is not USB Serial/JTAG"
require_line '^  hardware_uart: UART0$' \
  "${resolved_dir}/factory-esp32.yaml" "ESP32 bridge Improv transport is not UART0"
if grep -q 'next_url:' \
    "${resolved_dir}/factory-s3.yaml" "${resolved_dir}/factory-esp32.yaml"; then
  echo "Public factory Improv must not expose a next_url." >&2
  exit 1
fi

cp "${repo_dir}/esphome/.esphome/build/passion_wave_factory_s3/build/firmware.factory.bin" \
  "${output_dir}/s3/passion-wave-rotaryknob-s3.factory.bin"
cp "${repo_dir}/esphome/.esphome/build/passion_wave_factory_esp32/build/firmware.factory.bin" \
  "${output_dir}/esp32/passion-wave-rotaryknob-esp32.factory.bin"

# ESP Web Tools erases new installations by default. Setting this field to
# true would offer a choice and could preserve stale NVS credentials.
cat > "${output_dir}/s3/manifest.json" <<EOF
{
  "name": "PassionWave Rotaryknob",
  "version": "${version}",
  "new_install_prompt_erase": false,
  "new_install_improv_wait_time": 120,
  "builds": [
    {
      "chipFamily": "ESP32-S3",
      "parts": [
        { "path": "passion-wave-rotaryknob-s3.factory.bin", "offset": 0 }
      ]
    }
  ]
}
EOF

cat > "${output_dir}/esp32/manifest.json" <<EOF
{
  "name": "PassionWave Rotaryknob Bridge",
  "version": "${version}",
  "new_install_prompt_erase": false,
  "new_install_improv_wait_time": 120,
  "builds": [
    {
      "chipFamily": "ESP32",
      "parts": [
        { "path": "passion-wave-rotaryknob-esp32.factory.bin", "offset": 0 }
      ]
    }
  ]
}
EOF

python3 -m json.tool "${output_dir}/s3/manifest.json" >/dev/null
python3 -m json.tool "${output_dir}/esp32/manifest.json" >/dev/null

(
  cd "${output_dir}"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum \
      s3/passion-wave-rotaryknob-s3.factory.bin \
      esp32/passion-wave-rotaryknob-esp32.factory.bin > SHA256SUMS
  else
    shasum -a 256 \
      s3/passion-wave-rotaryknob-s3.factory.bin \
      esp32/passion-wave-rotaryknob-esp32.factory.bin > SHA256SUMS
  fi
)

echo "Public release artifacts: ${output_dir}"
