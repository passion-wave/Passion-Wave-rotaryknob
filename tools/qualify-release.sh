#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output_dir="${1:-${repo_dir}/release/public}"
version="$(tr -d '[:space:]' < "${repo_dir}/VERSION")"
integration_version="${version/-beta./b}"
esphome_image="${ESPHOME_IMAGE:-ghcr.io/esphome/esphome:2026.7.0}"
ha_images=(
  "ghcr.io/home-assistant/home-assistant:2026.7.4"
  "ghcr.io/home-assistant/home-assistant:2026.8.2"
)
factory_profiles=(
  "esphome/factory-s3.yaml"
  "esphome/factory-esp32.yaml"
)
managed_profiles=(
  "esphome/managed-production-s3.yaml"
  "esphome/managed-production-esp32.yaml"
  "esphome/managed-test-s3.yaml"
  "esphome/managed-test-esp32.yaml"
)
versioned_profiles=(
  "esphome/dual-mcu-esp32-core.yaml"
  "esphome/dual-mcu-s3-core.yaml"
  "esphome/factory-s3.yaml"
  "esphome/factory-esp32.yaml"
  "esphome/managed-production-s3.yaml"
  "esphome/managed-production-esp32.yaml"
  "esphome/managed-test-s3.yaml"
  "esphome/managed-test-esp32.yaml"
  "esphome/rotaryknob-s3-ui-core.yaml"
)
log_dir="$(mktemp -d)"

cleanup() {
  rm -rf "${log_dir}"
}
trap cleanup EXIT

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command is missing: $1" >&2
    exit 2
  fi
}

require_command docker
require_command git
require_command jq
require_command python3
require_command shasum

cd "${repo_dir}"
git diff --check

if [[ "$(jq -r '.version' custom_components/passion_wave/manifest.json)" != "${integration_version}" ]]; then
  echo "Integration manifest version does not match ${version}." >&2
  exit 3
fi
if ! grep -Fqx "INTEGRATION_VERSION = \"${version}\"" custom_components/passion_wave/const.py; then
  echo "Integration constant does not match ${version}." >&2
  exit 3
fi
for profile in "${versioned_profiles[@]}"; do
  if ! grep -Fq "${version}" "${profile}"; then
    echo "Firmware version is missing from ${profile}." >&2
    exit 3
  fi
done

echo "==> Home Assistant integration tests"
test_pids=()
test_labels=()
for image in "${ha_images[@]}"; do
  label="${image##*:}"
  test_labels+=("${label}")
  docker run --rm \
    -e PYTHONPATH=/work \
    -v "${repo_dir}":/work \
    -w /work \
    "${image}" \
    pytest -q tests >"${log_dir}/ha-${label}.log" 2>&1 &
  test_pids+=("$!")
done

test_failed=0
for index in "${!test_pids[@]}"; do
  if ! wait "${test_pids[$index]}"; then
    test_failed=1
  fi
  echo "--- Home Assistant ${test_labels[$index]} ---"
  cat "${log_dir}/ha-${test_labels[$index]}.log"
done
if [[ ${test_failed} -ne 0 ]]; then
  echo "Home Assistant integration tests failed." >&2
  exit 4
fi

echo "==> Validate all six ESPHome profiles"
for profile in "${factory_profiles[@]}" "${managed_profiles[@]}"; do
  "${repo_dir}/tools/config.sh" "${profile}" >/dev/null
  echo "validated ${profile}"
done

echo "==> Compile the four managed endpoint profiles"
for profile in "${managed_profiles[@]}"; do
  "${repo_dir}/tools/build.sh" "${profile}"
done

echo "==> Compile factory profiles and assemble public artifacts"
ESPHOME_IMAGE="${esphome_image}" \
  "${repo_dir}/tools/build-public-release.sh" "${output_dir}"

python3 -m json.tool "${output_dir}/s3/manifest.json" >/dev/null
python3 -m json.tool "${output_dir}/esp32/manifest.json" >/dev/null
if [[ "$(jq -r '.version' "${output_dir}/s3/manifest.json")" != "${version}" ]] ||
   [[ "$(jq -r '.version' "${output_dir}/esp32/manifest.json")" != "${version}" ]]; then
  echo "Generated public manifests do not match ${version}." >&2
  exit 5
fi

(
  cd "${output_dir}"
  shasum -a 256 -c SHA256SUMS
)

git diff --check
echo "Release candidate ${version} is qualified."
