#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
canonical_dir=""
if [[ "${1:-}" == "--canonical" ]]; then
  [[ $# -eq 2 ]] || { echo "Usage: $0 [--canonical DIR]" >&2; exit 2; }
  canonical_dir="$2"
elif [[ $# -ne 0 ]]; then
  echo "Usage: $0 [--canonical DIR]" >&2
  exit 2
fi
source "${repo_dir}/tools/release-toolchain.env"
[[ -z "$(git -C "${repo_dir}" status --porcelain --untracked-files=no)" ]] || {
  echo "RC reproducibility requires a clean tracked worktree." >&2; exit 6;
}
scratch="$(mktemp -d "${TMPDIR:-/tmp}/passion-wave-repro.XXXXXX")"
failure_dir="${repo_dir}/.release-pipeline/repro-failures/$(date -u +%Y%m%dT%H%M%SZ)"
cleanup() {
  for worktree in "${scratch}/source-a" "${scratch}/source-b"; do
    if [[ -d "${worktree}" ]]; then git -C "${repo_dir}" worktree remove --force "${worktree}" >/dev/null 2>&1 || true; fi
  done
  rm -rf "${scratch}"
}
trap cleanup EXIT
source_date_epoch="$(git -C "${repo_dir}" show -s --format=%ct HEAD)"
platform_key="${ESPHOME_PLATFORM_DEFAULT//\//-}"
shared_platformio_cache="${repo_dir}/.esphome_cache/${platform_key}/platformio"
shared_esphome_cache="${repo_dir}/.esphome_cache/${platform_key}/esphome"
mkdir -p "${shared_platformio_cache}"

preserve_failure() {
  mkdir -p "${failure_dir}"
  for run in a b; do
    [[ ! -d "${scratch}/output-${run}" ]] || cp -a "${scratch}/output-${run}" "${failure_dir}/output-${run}"
    [[ ! -f "${scratch}/build-${run}.log" ]] || cp "${scratch}/build-${run}.log" "${failure_dir}/"
    for role in passion_wave_factory_s3 passion_wave_factory_esp32; do
      build_root="${scratch}/source-${run}/esphome/.esphome/build/${role}"
      [[ ! -f "${build_root}/build_info.json" ]] || cp "${build_root}/build_info.json" "${failure_dir}/${run}-${role}-build_info.json"
      [[ ! -f "${build_root}/build/firmware.elf" ]] || cp "${build_root}/build/firmware.elf" "${failure_dir}/${run}-${role}.elf"
      [[ ! -f "${build_root}/build/firmware.map" ]] || cp "${build_root}/build/firmware.map" "${failure_dir}/${run}-${role}.map"
    done
  done
  echo "Reproducibility diagnostics preserved at ${failure_dir}" >&2
}

for run in a b; do
  git -C "${repo_dir}" worktree add --detach "${scratch}/source-${run}" HEAD >/dev/null
done
build_pids=()
for run in a b; do
  SOURCE_DATE_EPOCH="${source_date_epoch}" PLATFORMIO_CACHE="${shared_platformio_cache}" \
    ESPHOME_CACHE="${shared_esphome_cache}" CCACHE_DISABLE=1 \
    ESPHOME_IMAGE="${ESPHOME_IMAGE:-${ESPHOME_IMAGE_DEFAULT}}" \
    "${scratch}/source-${run}/tools/build-public-release.sh" "${scratch}/output-${run}" \
    >"${scratch}/build-${run}.log" 2>&1 &
  build_pids+=("$!")
done
build_failed=0
for pid in "${build_pids[@]}"; do wait "${pid}" || build_failed=1; done
if [[ ${build_failed} -ne 0 ]]; then preserve_failure; exit 7; fi
cmp -s "${scratch}/output-a/SHA256SUMS" "${scratch}/output-b/SHA256SUMS" || {
  diff -u "${scratch}/output-a/SHA256SUMS" "${scratch}/output-b/SHA256SUMS" >&2 || true
  preserve_failure
  echo "RC binaries are not reproducible." >&2
  exit 7
}
for evidence in build-metadata.json sbom.cdx.json; do
  cmp -s "${scratch}/output-a/${evidence}" "${scratch}/output-b/${evidence}" || {
    preserve_failure
    echo "RC provenance is not reproducible: ${evidence}" >&2
    exit 7
  }
done
if [[ -n "${canonical_dir}" ]]; then
  [[ -f "${canonical_dir}/SHA256SUMS" ]] || {
    echo "Qualified canonical output is missing: ${canonical_dir}" >&2; exit 7;
  }
  cmp -s "${scratch}/output-a/SHA256SUMS" "${canonical_dir}/SHA256SUMS" || {
    echo "Clean reproducibility output differs from the qualified canonical output." >&2
    preserve_failure
    exit 7
  }
fi
echo "REPRODUCIBLE source=$(git -C "${repo_dir}" rev-parse HEAD) epoch=${source_date_epoch}"
