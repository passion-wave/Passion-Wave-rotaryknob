#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${repo_dir}/tools/release-toolchain.env"
source "${repo_dir}/tools/example-secrets-fixture.sh"
channel="beta"
output_dir="${repo_dir}/release/public"
log_dir="${repo_dir}/.release-pipeline/qualify"

usage() {
  echo "Usage: $0 --channel alpha|beta|rc [--output DIR] [--log-dir DIR]" >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --channel) channel="${2:-}"; shift 2 ;;
    --output) output_dir="${2:-}"; shift 2 ;;
    --log-dir) log_dir="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) usage; exit 2 ;;
  esac
done
case "${channel}" in alpha|beta|rc) ;; *) usage; exit 2 ;; esac

version="$(tr -d '[:space:]' < "${repo_dir}/VERSION")"
case "${version}" in
  *-alpha.*) version_channel="alpha"; integration_version="${version/-alpha./a}" ;;
  *-beta.*) version_channel="beta"; integration_version="${version/-beta./b}" ;;
  *-rc.*) version_channel="rc"; integration_version="${version/-rc./rc}" ;;
  *) echo "Unsupported prerelease version: ${version}" >&2; exit 3 ;;
esac
if [[ "${version_channel}" != "${channel}" ]]; then
  echo "VERSION ${version} does not match channel ${channel}." >&2
  exit 3
fi

esphome_image="${ESPHOME_IMAGE:-${ESPHOME_IMAGE_DEFAULT}}"
ha_images=("${HA_IMAGE_CURRENT:-${HA_IMAGE_CURRENT_DEFAULT}}")
if [[ "${channel}" != "alpha" ]]; then
  ha_images=("${HA_IMAGE_BASELINE:-${HA_IMAGE_BASELINE_DEFAULT}}" "${HA_IMAGE_CURRENT:-${HA_IMAGE_CURRENT_DEFAULT}}")
fi
factory_profiles=(esphome/factory-s3.yaml esphome/factory-esp32.yaml)
managed_profiles=(
  esphome/managed-production-s3.yaml esphome/managed-production-esp32.yaml
  esphome/managed-test-s3.yaml esphome/managed-test-esp32.yaml
)
versioned_profiles=(
  esphome/dual-mcu-esp32-core.yaml esphome/dual-mcu-s3-core.yaml
  "${factory_profiles[@]}" "${managed_profiles[@]}" esphome/rotaryknob-s3-ui-core.yaml
)

mkdir -p "${log_dir}"

require_command() {
  command -v "$1" >/dev/null 2>&1 || { echo "Required command is missing: $1" >&2; exit 2; }
}

fail_log() {
  local label="$1" log="$2" code="${3:-1}"
  echo "FAIL ${label}; last log lines:" >&2
  tail -n 30 "${log}" >&2 || true
  exit "${code}"
}

run_logged() {
  local label="$1" log="$2"
  shift 2
  local started
  started="$(date +%s)"
  if "$@" >"${log}" 2>&1; then
    echo "PASS ${label} ($(( $(date +%s) - started ))s)"
  else
    fail_log "${label}" "${log}" "$?"
  fi
}

for command in docker git jq python3 shasum; do require_command "${command}"; done
cd "${repo_dir}"
git diff --check
if git ls-files --error-unmatch esphome/secrets.yaml >/dev/null 2>&1; then
  echo "Tracked esphome/secrets.yaml is forbidden." >&2
  exit 3
fi
pw_setup_example_secrets "${repo_dir}"
trap pw_cleanup_example_secrets EXIT INT TERM

[[ "$(jq -r '.version' custom_components/passion_wave/manifest.json)" == "${integration_version}" ]] \
  || { echo "Integration manifest version does not match ${version}." >&2; exit 3; }
grep -Fqx "INTEGRATION_VERSION = \"${version}\"" custom_components/passion_wave/const.py \
  || { echo "Integration constant does not match ${version}." >&2; exit 3; }
for profile in "${versioned_profiles[@]}"; do
  grep -Fq "${version}" "${profile}" \
    || { echo "Firmware version is missing from ${profile}." >&2; exit 3; }
done
echo "PASS metadata (${version}, ${channel})"

echo "== Home Assistant matrix (${#ha_images[@]} runners) =="
test_pids=()
test_labels=()
for image in "${ha_images[@]}"; do
  tag="${image%%@*}"
  label="${tag##*:}"
  test_labels+=("${label}")
  docker run --rm -e PYTHONPATH=/work -v "${repo_dir}":/work -w /work "${image}" \
    pytest -q tests >"${log_dir}/ha-${label}.log" 2>&1 &
  test_pids+=("$!")
done
test_failed=0
for index in "${!test_pids[@]}"; do
  if wait "${test_pids[$index]}"; then
    echo "PASS ha-${test_labels[$index]}"
  else
    test_failed=1
    echo "FAIL ha-${test_labels[$index]}" >&2
    tail -n 30 "${log_dir}/ha-${test_labels[$index]}.log" >&2 || true
  fi
done
[[ ${test_failed} -eq 0 ]] || exit 4

echo "== ESPHome configuration matrix =="
for profile in "${factory_profiles[@]}" "${managed_profiles[@]}"; do
  label="$(basename "${profile}" .yaml)"
  ESPHOME_IMAGE="${esphome_image}" run_logged "config-${label}" "${log_dir}/config-${label}.log" \
    "${repo_dir}/tools/config.sh" "${profile}"
done

if [[ "${channel}" != "alpha" ]]; then
  echo "== Managed endpoint builds =="
  for pair in "esphome/managed-production-s3.yaml esphome/managed-production-esp32.yaml" \
              "esphome/managed-test-s3.yaml esphome/managed-test-esp32.yaml"; do
    read -r s3_profile bridge_profile <<<"${pair}"
    s3_label="$(basename "${s3_profile}" .yaml)"
    bridge_label="$(basename "${bridge_profile}" .yaml)"
    ESPHOME_IMAGE="${esphome_image}" "${repo_dir}/tools/build.sh" "${s3_profile}" \
      >"${log_dir}/build-${s3_label}.log" 2>&1 & s3_pid=$!
    ESPHOME_IMAGE="${esphome_image}" "${repo_dir}/tools/build.sh" "${bridge_profile}" \
      >"${log_dir}/build-${bridge_label}.log" 2>&1 & bridge_pid=$!
    pair_failed=0
    wait "${s3_pid}" || pair_failed=1
    wait "${bridge_pid}" || pair_failed=1
    if [[ ${pair_failed} -ne 0 ]]; then
      tail -n 30 "${log_dir}/build-${s3_label}.log" >&2 || true
      tail -n 30 "${log_dir}/build-${bridge_label}.log" >&2 || true
      exit 5
    fi
    echo "PASS build-${s3_label} + build-${bridge_label}"
  done
fi

ESPHOME_IMAGE="${esphome_image}" run_logged public-artifacts "${log_dir}/public-artifacts.log" \
  "${repo_dir}/tools/build-public-release.sh" "${output_dir}"

python3 -m json.tool "${output_dir}/s3/manifest.json" >/dev/null
python3 -m json.tool "${output_dir}/esp32/manifest.json" >/dev/null
[[ "$(jq -r '.version' "${output_dir}/s3/manifest.json")" == "${version}" ]]
[[ "$(jq -r '.version' "${output_dir}/esp32/manifest.json")" == "${version}" ]]
(cd "${output_dir}" && shasum -a 256 -c SHA256SUMS >/dev/null)

if [[ "${channel}" == "rc" ]]; then
  run_logged reproducibility "${log_dir}/reproducibility.log" \
    "${repo_dir}/tools/reproducible-public-release.sh" --canonical "${output_dir}"
fi

git diff --check
echo "QUALIFIED ${version} channel=${channel} logs=${log_dir}"
