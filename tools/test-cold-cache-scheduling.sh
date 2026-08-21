#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
script="${root}/tools/qualify-release.sh"
public_builder="${root}/tools/build-public-release.sh"

warmup_line="$(grep -n 'warmup_profile="esphome/managed-production-s3.yaml"' "${script}" | cut -d: -f1)"
cleanup_line="$(grep -n 'cleanup_managed_build "${warmup_label//-/_}"' "${script}" | cut -d: -f1)"
first_group_line="$(grep -n 'first_managed_group=(' "${script}" | cut -d: -f1)"
[[ -n "${warmup_line}" && -n "${cleanup_line}" && -n "${first_group_line}" ]]
[[ ${warmup_line} -lt ${cleanup_line} && ${cleanup_line} -lt ${first_group_line} ]]

for profile in managed-production-esp32 managed-test-s3 managed-test-esp32; do
  grep -Fq "esphome/${profile}.yaml" "${script}"
done
for build_name in managed_production_s3 managed_production_esp32 managed_test_s3 managed_test_esp32; do
  grep -Fq "${build_name}" "${script}"
done
grep -Fq -- '--entrypoint sh' "${script}"
grep -Fq -- '-v "${managed_build_root}:/build"' "${script}"
grep -Fq 'df -Pk "${managed_build_root}"' "${script}"
grep -Fq 'run_managed_group first-managed "${first_managed_group[@]}"' "${script}"
grep -Fq 'run_managed_group second-managed "${second_managed_group[@]}"' "${script}"
if grep -Fq 'rm -rf -- "${build_dir}"' "${script}"; then
  echo "Managed build cleanup must not run as the unprivileged host user." >&2
  exit 1
fi
grep -Fq 'PASS cleanup-${build_id}' "${script}"
grep -Fq 'PW_PARALLEL_FACTORY_BUILDS=1' "${script}"
grep -Fq 'wait_factory_pair' "${public_builder}"
grep -Fq 'PW_PARALLEL_FACTORY_BUILDS:-0' "${public_builder}"

echo "PASS cold-cache warmup, bounded parallel builds and root-safe cleanup."
