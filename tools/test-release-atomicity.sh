#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
scratch="$(mktemp -d "${TMPDIR:-/tmp}/passion-wave-firmware-fault.XXXXXX")"
trap 'rm -rf "${scratch}"' EXIT
mkdir -p "${scratch}/public"
printf 'last-good\n' >"${scratch}/public/sentinel"
before="$(shasum -a 256 "${scratch}/public/sentinel" | awk '{print $1}')"
if ESPHOME_COMMAND=/usr/bin/false \
    "${repo_dir}/tools/build-public-release.sh" "${scratch}/public" \
    >"${scratch}/failure.log" 2>&1; then
  echo "Injected firmware build failure unexpectedly succeeded." >&2
  exit 1
fi
after="$(shasum -a 256 "${scratch}/public/sentinel" | awk '{print $1}')"
[[ "${before}" == "${after}" ]] || {
  echo "Failed firmware build changed the stable artifact tree." >&2
  exit 1
}
echo "PASS firmware build fault injection: stable tree unchanged"
