#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${repo_dir}/tools/release-toolchain.env"
source "${repo_dir}/tools/example-secrets-fixture.sh"
scope="all"
log_dir="${repo_dir}/.release-pipeline/fast-check"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --scope) scope="${2:-}"; shift 2 ;;
    --log-dir) log_dir="${2:-}"; shift 2 ;;
    *) echo "Usage: $0 --scope integration,s3,bridge|all [--log-dir DIR]" >&2; exit 2 ;;
  esac
done
mkdir -p "${log_dir}"
version="$(tr -d '[:space:]' < "${repo_dir}/VERSION")"
case "${version}" in
  *-alpha.*) integration_version="${version/-alpha./a}" ;;
  *-beta.*) integration_version="${version/-beta./b}" ;;
  *-rc.*) integration_version="${version/-rc./rc}" ;;
  *) echo "Unsupported prerelease version: ${version}" >&2; exit 3 ;;
esac
has_scope() { [[ ",${scope}," == *",$1,"* || "${scope}" == "all" ]]; }
run() {
  local label="$1"; shift
  if "$@" >"${log_dir}/${label}.log" 2>&1; then echo "PASS ${label}"
  else tail -n 30 "${log_dir}/${label}.log" >&2 || true; exit 4; fi
}
cd "${repo_dir}"
git diff --check
if git ls-files --error-unmatch esphome/secrets.yaml >/dev/null 2>&1; then
  echo "Tracked esphome/secrets.yaml is forbidden." >&2
  exit 3
fi
pw_setup_example_secrets "${repo_dir}"
trap pw_cleanup_example_secrets EXIT INT TERM
[[ "$(jq -r '.version' custom_components/passion_wave/manifest.json)" == "${integration_version}" ]]
grep -Fqx "INTEGRATION_VERSION = \"${version}\"" custom_components/passion_wave/const.py

if has_scope integration; then
  run ha-current docker run --rm -e PYTHONPATH=/work -v "${repo_dir}":/work -w /work \
    "${HA_IMAGE_CURRENT:-${HA_IMAGE_CURRENT_DEFAULT}}" pytest -q tests
fi
if has_scope s3; then
  for profile in esphome/factory-s3.yaml esphome/managed-production-s3.yaml esphome/managed-test-s3.yaml; do
    label="config-$(basename "${profile}" .yaml)"
    run "${label}" env ESPHOME_IMAGE="${ESPHOME_IMAGE:-${ESPHOME_IMAGE_DEFAULT}}" \
      "${repo_dir}/tools/config.sh" "${profile}"
  done
  run build-s3 env ESPHOME_IMAGE="${ESPHOME_IMAGE:-${ESPHOME_IMAGE_DEFAULT}}" \
    "${repo_dir}/tools/build.sh" esphome/factory-s3.yaml
fi
if has_scope bridge; then
  for profile in esphome/factory-esp32.yaml esphome/managed-production-esp32.yaml esphome/managed-test-esp32.yaml; do
    label="config-$(basename "${profile}" .yaml)"
    run "${label}" env ESPHOME_IMAGE="${ESPHOME_IMAGE:-${ESPHOME_IMAGE_DEFAULT}}" \
      "${repo_dir}/tools/config.sh" "${profile}"
  done
  run build-bridge env ESPHOME_IMAGE="${ESPHOME_IMAGE:-${ESPHOME_IMAGE_DEFAULT}}" \
    "${repo_dir}/tools/build.sh" esphome/factory-esp32.yaml
fi
echo "FAST-CHECK scope=${scope} logs=${log_dir}"
