#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${repo_dir}/tools/example-secrets-fixture.sh"
scratch="$(mktemp -d "${TMPDIR:-/tmp}/passion-wave-secrets-test.XXXXXX")"
trap 'rm -rf "${scratch}"' EXIT
mkdir -p "${scratch}/esphome/devices"
cp "${repo_dir}/esphome/secrets.example.yaml" "${scratch}/esphome/secrets.example.yaml"

pw_setup_example_secrets "${scratch}"
[[ -f "${scratch}/esphome/secrets.yaml" ]]
[[ -f "${scratch}/esphome/devices/secrets.yaml" ]]
pw_cleanup_example_secrets
[[ ! -e "${scratch}/esphome/secrets.yaml" ]]
[[ ! -e "${scratch}/esphome/devices/secrets.yaml" ]]

printf 'wifi_ssid: "real-sentinel"\n' >"${scratch}/esphome/secrets.yaml"
pw_setup_example_secrets "${scratch}"
grep -Fq 'real-sentinel' "${scratch}/esphome/secrets.yaml"
[[ ! -e "${scratch}/esphome/devices/secrets.yaml" ]]
pw_cleanup_example_secrets
grep -Fq 'real-sentinel' "${scratch}/esphome/secrets.yaml"
echo "PASS example secrets fixture lifecycle and real-secret preservation"
