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

if grep -q '^[[:space:]]*encryption:' \
    "${resolved_dir}/factory-s3.yaml" "${resolved_dir}/factory-esp32.yaml"; then
  echo "Public factory API must not contain an encryption key." >&2
  exit 1
fi

grep -q 'friendly_name: PassionWave Rotaryknob$' \
  "${resolved_dir}/factory-s3.yaml"
grep -q 'friendly_name: PassionWave Rotaryknob Bridge$' \
  "${resolved_dir}/factory-esp32.yaml"
grep -q 'name_add_mac_suffix: true' "${resolved_dir}/factory-s3.yaml"
grep -q 'name_add_mac_suffix: true' "${resolved_dir}/factory-esp32.yaml"

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
  "home_assistant_domain": "esphome",
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
  "home_assistant_domain": "esphome",
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
