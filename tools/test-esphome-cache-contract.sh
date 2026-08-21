#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
common="${root}/tools/esphome-common.sh"

grep -Fq 'CCACHE_CACHE=' "${common}"
grep -Fq ':/root/.ccache' "${common}"
grep -Fq 'CCACHE_DIR=/root/.ccache' "${common}"
grep -Fq 'CCACHE_DISABLE=1' "${root}/.github/workflows/rc-reproducibility.yml"
grep -Fq 'CCACHE_DISABLE=1' "${root}/tools/reproducible-public-release.sh"

echo "PASS shared ccache accelerates normal builds and remains disabled for reproducibility."
