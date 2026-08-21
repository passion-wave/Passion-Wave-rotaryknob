#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
script="${root}/tools/build-public-release.sh"

epoch_line="$(grep -n '^SOURCE_DATE_EPOCH=' "${script}" | head -n 1 | cut -d: -f1)"
export_line="$(grep -n '^export SOURCE_DATE_EPOCH$' "${script}" | head -n 1 | cut -d: -f1)"
first_build_line="$(grep -n '^clean_factory_builds$' "${script}" | head -n 1 | cut -d: -f1)"

[[ -n "${epoch_line}" && -n "${export_line}" && -n "${first_build_line}" ]]
[[ ${epoch_line} -lt ${export_line} && ${export_line} -lt ${first_build_line} ]]

if grep -q '^SOURCE_DATE_EPOCH=.*ESPHOME_IMAGE_RESOLVED=' "${script}"; then
  echo "SOURCE_DATE_EPOCH must be exported before compilation, not only metadata generation." >&2
  exit 1
fi

echo "PASS public build exports the commit epoch before ESPHome compilation."
