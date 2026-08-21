#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
common="${root}/tools/esphome-common.sh"

grep -Fq 'CCACHE_CACHE=' "${common}"
grep -Fq ':/root/.ccache' "${common}"
grep -Fq 'CCACHE_DIR=/root/.ccache' "${common}"
grep -Fq 'IDF_CCACHE_ENABLE=1' "${common}"
grep -Fq 'PLATFORMIO_BUILD_CACHE_DIR=/root/.platformio/build-cache' "${common}"
disable_line="$(grep -n 'if \[\[ -n "${CCACHE_DISABLE:-}" \]\]' "${common}" | cut -d: -f1)"
enable_line="$(grep -n 'IDF_CCACHE_ENABLE=1' "${common}" | cut -d: -f1)"
[[ -n "${disable_line}" && -n "${enable_line}" && ${disable_line} -lt ${enable_line} ]]
grep -Fq 'CCACHE_DISABLE=1' "${root}/.github/workflows/rc-reproducibility.yml"
grep -Fq 'CCACHE_DISABLE=1' "${root}/tools/reproducible-public-release.sh"
grep -Fq 'export CCACHE_DISABLE=1' "${root}/tools/build-public-release.sh"
grep -Fq 'passion_wave_factory_s3 passion_wave_factory_esp32' \
  "${root}/tools/build-public-release.sh"
grep -Fq 'ESPHOME_PLATFORM_DEFAULT="linux/amd64"' "${root}/tools/release-toolchain.env"
grep -Fq -- '--platform "${ESPHOME_PLATFORM}"' "${common}"
grep -Fq 'ESPHOME_PLATFORM_RESOLVED' "${root}/tools/build-public-release.sh"

normal_args="$(bash -c '
  source "$1"
  docker() { printf "%s\n" "$@"; }
  docker_esphome version
' _ "${common}")"
grep -Fq 'IDF_CCACHE_ENABLE=1' <<<"${normal_args}"
grep -Fq 'PLATFORMIO_BUILD_CACHE_DIR=/root/.platformio/build-cache' <<<"${normal_args}"
grep -Fq -- '--platform' <<<"${normal_args}"
grep -Fq 'linux/amd64' <<<"${normal_args}"

repro_args="$(CCACHE_DISABLE=1 bash -c '
  source "$1"
  docker() { printf "%s\n" "$@"; }
  docker_esphome version
' _ "${common}")"
grep -Fq 'CCACHE_DISABLE=1' <<<"${repro_args}"
if grep -Fq 'IDF_CCACHE_ENABLE=1' <<<"${repro_args}" ||
   grep -Fq 'PLATFORMIO_BUILD_CACHE_DIR=' <<<"${repro_args}"; then
  echo "Reproducibility mode must not enable compiler build caches." >&2
  exit 1
fi

echo "PASS ESP-IDF and PlatformIO caches accelerate normal builds and remain disabled for reproducibility."
