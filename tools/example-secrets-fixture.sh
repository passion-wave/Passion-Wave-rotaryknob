#!/usr/bin/env bash
# Source from validation scripts. Creates only missing CI placeholders and
# removes only files created by this process; real local secrets are untouched.

PW_EXAMPLE_SECRETS_CREATED=()

pw_setup_example_secrets() {
  local repo_dir="$1"
  local example="${repo_dir}/esphome/secrets.example.yaml"
  local root_secret="${repo_dir}/esphome/secrets.yaml"
  local device_secret="${repo_dir}/esphome/devices/secrets.yaml"
  [[ -f "${example}" ]] || { echo "Missing public secrets fixture: ${example}" >&2; return 3; }

  # A maintainer's real root secret is ESPHome's authority. Never supplement,
  # shadow or overwrite it with examples.
  [[ -e "${root_secret}" ]] && return 0
  cp "${example}" "${root_secret}"
  PW_EXAMPLE_SECRETS_CREATED+=("${root_secret}")
  if [[ ! -e "${device_secret}" ]]; then
    cp "${example}" "${device_secret}"
    PW_EXAMPLE_SECRETS_CREATED+=("${device_secret}")
  fi
}

pw_cleanup_example_secrets() {
  local path
  if [[ -n "${PW_EXAMPLE_SECRETS_CREATED[*]-}" ]]; then
    for path in "${PW_EXAMPLE_SECRETS_CREATED[@]}"; do rm -f "${path}"; done
  fi
  PW_EXAMPLE_SECRETS_CREATED=()
}
