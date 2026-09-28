#!/usr/bin/env bash
set -euo pipefail
avatar_repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if ! command -v c++ >/dev/null && ! command -v g++ >/dev/null && ! command -v clang++ >/dev/null; then
  echo "Weather avatar native regression gate requires a C++17 host compiler." >&2
  exit 1
fi
cd "${avatar_repo_root}"
PYTHONPATH="${avatar_repo_root}/tests${PYTHONPATH:+:${PYTHONPATH}}" python3 -m unittest \
  test_weather_avatar_resolver test_weather_avatar_schedule \
  test_weather_avatar_transport test_weather_avatar_renderer
