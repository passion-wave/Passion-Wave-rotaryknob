#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${repo_dir}/tools/release-toolchain.env"
# The public build is also a supported standalone diagnostic entrypoint. Set
# the commit epoch before any ESPHome process starts; setting it only while
# writing build-metadata.json makes the metadata deterministic but leaves the
# embedded build_info timestamp dependent on the host clock.
SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-$(git -C "${repo_dir}" show -s --format=%ct HEAD)}"
export SOURCE_DATE_EPOCH
# Public release payloads must never reuse cached objects: generated sources
# embed SOURCE_DATE_EPOCH and a stale ccache entry can otherwise produce a
# self-consistent but non-reproducible candidate.
export CCACHE_DISABLE=1
requested_output="${1:-${repo_dir}/release/public}"
mkdir -p "$(dirname "${requested_output}")"
output_parent="$(cd "$(dirname "${requested_output}")" && pwd)"
output_name="$(basename "${requested_output}")"
final_output_dir="${output_parent}/${output_name}"
lock_dir="${output_parent}/.${output_name}.build.lock"
mkdir "${lock_dir}" 2>/dev/null || {
  echo "Public artifact build is already running for ${final_output_dir}." >&2
  exit 75
}
output_dir="$(mktemp -d "${output_parent}/.${output_name}.stage.XXXXXX")"
if [[ -d "${final_output_dir}" ]]; then
  cp -a "${final_output_dir}/." "${output_dir}/"
fi
version="$(tr -d '[:space:]' < "${repo_dir}/VERSION")"
resolved_dir="$(mktemp -d)"
s3_binary="passion-wave-rotaryknob-s3-${version}.factory.bin"
esp32_binary="passion-wave-rotaryknob-esp32-${version}.factory.bin"
s3_ota_binary="passion-wave-rotaryknob-s3-${version}.ota.bin"
esp32_ota_binary="passion-wave-rotaryknob-esp32-${version}.ota.bin"
s3_manifest="manifest-${version}.json"
esp32_manifest="manifest-${version}.json"

cleanup() {
  rm -f "${resolved_dir}/factory-s3.yaml" "${resolved_dir}/factory-esp32.yaml"
  rmdir "${resolved_dir}"
  rm -rf "${output_dir}"
  rmdir "${lock_dir}" 2>/dev/null || true
}
trap cleanup EXIT

require_line() {
  local pattern="$1"
  local file="$2"
  local description="$3"

  if ! grep -q "${pattern}" "${file}"; then
    echo "Public factory validation failed: ${description}." >&2
    exit 1
  fi
}

mkdir -p "${output_dir}/s3" "${output_dir}/esp32"

clean_factory_builds() {
  local build_root="${repo_dir}/esphome/.esphome/build" role
  for role in passion_wave_factory_s3 passion_wave_factory_esp32; do
    [[ ! -d "${build_root}/${role}" ]] && continue
    rm -rf -- "${build_root:?}/${role}" 2>/dev/null || true
    [[ ! -d "${build_root}/${role}" ]] || docker run --rm \
      --platform "${ESPHOME_PLATFORM:-${ESPHOME_PLATFORM_DEFAULT}}" \
      -v "${build_root}:/build" \
      --entrypoint sh \
      "${ESPHOME_IMAGE:-${ESPHOME_IMAGE_DEFAULT}}" \
      -c 'rm -rf -- "/build/$1"' sh "${role}"
  done
}

clean_factory_builds

if [[ -n "${ESPHOME_COMMAND:-}" ]]; then
  "${ESPHOME_COMMAND}" config "${repo_dir}/esphome/factory-s3.yaml" \
    > "${resolved_dir}/factory-s3.yaml"
  "${ESPHOME_COMMAND}" config "${repo_dir}/esphome/factory-esp32.yaml" \
    > "${resolved_dir}/factory-esp32.yaml"
  "${ESPHOME_COMMAND}" compile "${repo_dir}/esphome/factory-s3.yaml"
  "${ESPHOME_COMMAND}" compile "${repo_dir}/esphome/factory-esp32.yaml"
else
  docker run --rm --platform "${ESPHOME_PLATFORM:-${ESPHOME_PLATFORM_DEFAULT}}" \
    -v "${repo_dir}":/config \
    "${ESPHOME_IMAGE:-${ESPHOME_IMAGE_DEFAULT}}" \
    config /config/esphome/factory-s3.yaml \
    > "${resolved_dir}/factory-s3.yaml"
  docker run --rm --platform "${ESPHOME_PLATFORM:-${ESPHOME_PLATFORM_DEFAULT}}" \
    -v "${repo_dir}":/config \
    "${ESPHOME_IMAGE:-${ESPHOME_IMAGE_DEFAULT}}" \
    config /config/esphome/factory-esp32.yaml \
    > "${resolved_dir}/factory-esp32.yaml"
  # Both deterministic builds mount one shared ESPHome tool cache. Running the
  # initial ESP-IDF installation concurrently can make one installer delete a
  # partially populated tool directory while the other still uses it. Build
  # S3 first, then reuse the complete cache for the Bridge.
  "${repo_dir}/tools/build.sh" esphome/factory-s3.yaml
  "${repo_dir}/tools/build.sh" esphome/factory-esp32.yaml
fi

for resolved_config in \
    "${resolved_dir}/factory-s3.yaml" "${resolved_dir}/factory-esp32.yaml"; do
  if ! awk '
    /^api:$/ { in_api = 1; next }
    in_api && /^[^[:space:]]/ { exit }
    in_api && /^  encryption: \{\}$/ { found = 1 }
    END { exit !found }
  ' "${resolved_config}"; then
    echo "Public factory API must enable runtime encryption without a compiled key: ${resolved_config}" >&2
    exit 1
  fi
  if ! grep -A1 '^provisioning:$' "${resolved_config}" \
      | grep -q '^  timeout: 20min$'; then
    echo "Public factory provisioning window must be 20min: ${resolved_config}" >&2
    exit 1
  fi
done

require_line 'friendly_name: PassionWave RotaryKnob$' \
  "${resolved_dir}/factory-s3.yaml" "S3 friendly name is missing"
require_line 'friendly_name: PassionWave RotaryKnob Bridge$' \
  "${resolved_dir}/factory-esp32.yaml" "ESP32 bridge friendly name is missing"
require_line 'name_add_mac_suffix: true' \
  "${resolved_dir}/factory-s3.yaml" "S3 MAC suffix is disabled"
require_line 'name_add_mac_suffix: true' \
  "${resolved_dir}/factory-esp32.yaml" "ESP32 bridge MAC suffix is disabled"
require_line '^improv_serial:' \
  "${resolved_dir}/factory-s3.yaml" "S3 Improv Serial is disabled"
require_line '^improv_serial:' \
  "${resolved_dir}/factory-esp32.yaml" "ESP32 bridge Improv Serial is disabled"
require_line '^  baud_rate: 115200$' \
  "${resolved_dir}/factory-s3.yaml" "S3 logger does not use 115200 baud"
require_line '^  baud_rate: 115200$' \
  "${resolved_dir}/factory-esp32.yaml" "ESP32 bridge logger does not use 115200 baud"
require_line '^  hardware_uart: USB_SERIAL_JTAG$' \
  "${resolved_dir}/factory-s3.yaml" "S3 Improv transport is not USB Serial/JTAG"
require_line '^  hardware_uart: UART0$' \
  "${resolved_dir}/factory-esp32.yaml" "ESP32 bridge Improv transport is not UART0"
if grep -q 'next_url:' \
    "${resolved_dir}/factory-s3.yaml" "${resolved_dir}/factory-esp32.yaml"; then
  echo "Public factory Improv must not expose a next_url." >&2
  exit 1
fi

cp "${repo_dir}/esphome/.esphome/build/passion_wave_factory_s3/build/firmware.factory.bin" \
  "${output_dir}/s3/${s3_binary}"
cp "${repo_dir}/esphome/.esphome/build/passion_wave_factory_esp32/build/firmware.factory.bin" \
  "${output_dir}/esp32/${esp32_binary}"
cp "${repo_dir}/esphome/.esphome/build/passion_wave_factory_s3/build/firmware.ota.bin" \
  "${output_dir}/s3/${s3_ota_binary}"
cp "${repo_dir}/esphome/.esphome/build/passion_wave_factory_esp32/build/firmware.ota.bin" \
  "${output_dir}/esp32/${esp32_ota_binary}"

if command -v md5sum >/dev/null 2>&1; then
  s3_ota_md5="$(md5sum "${output_dir}/s3/${s3_ota_binary}" | awk '{print $1}')"
  esp32_ota_md5="$(md5sum "${output_dir}/esp32/${esp32_ota_binary}" | awk '{print $1}')"
else
  s3_ota_md5="$(md5 -q "${output_dir}/s3/${s3_ota_binary}")"
  esp32_ota_md5="$(md5 -q "${output_dir}/esp32/${esp32_ota_binary}")"
fi

# ESP Web Tools erases new installations by default. Setting this field to
# true would offer a choice and could preserve stale NVS credentials.
cat > "${output_dir}/s3/${s3_manifest}" <<EOF
{
  "name": "PassionWave RotaryKnob",
  "version": "${version}",
  "new_install_prompt_erase": false,
  "new_install_improv_wait_time": 120,
  "builds": [
    {
      "chipFamily": "ESP32-S3",
      "parts": [
        { "path": "${s3_binary}", "offset": 0 }
      ],
      "ota": {
        "md5": "${s3_ota_md5}",
        "path": "${s3_ota_binary}",
        "release_url": "https://github.com/passion-wave/Passion-Wave-rotaryknob/releases/tag/v${version}",
        "summary": "PassionWave RotaryKnob ${version}"
      }
    }
  ]
}
EOF

cat > "${output_dir}/esp32/${esp32_manifest}" <<EOF
{
  "name": "PassionWave RotaryKnob Bridge",
  "version": "${version}",
  "new_install_prompt_erase": false,
  "new_install_improv_wait_time": 120,
  "builds": [
    {
      "chipFamily": "ESP32",
      "parts": [
        { "path": "${esp32_binary}", "offset": 0 }
      ],
      "ota": {
        "md5": "${esp32_ota_md5}",
        "path": "${esp32_ota_binary}",
        "release_url": "https://github.com/passion-wave/Passion-Wave-rotaryknob/releases/tag/v${version}",
        "summary": "PassionWave RotaryKnob Bridge ${version}"
      }
    }
  ]
}
EOF

python3 -m json.tool "${output_dir}/s3/${s3_manifest}" >/dev/null
python3 -m json.tool "${output_dir}/esp32/${esp32_manifest}" >/dev/null
cp "${output_dir}/s3/${s3_manifest}" "${output_dir}/s3/manifest.json"
cp "${output_dir}/esp32/${esp32_manifest}" "${output_dir}/esp32/manifest.json"

(
  cd "${output_dir}"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum \
      "s3/${s3_binary}" \
      "s3/${s3_ota_binary}" \
      "esp32/${esp32_binary}" \
      "esp32/${esp32_ota_binary}" > SHA256SUMS
  else
    shasum -a 256 \
      "s3/${s3_binary}" \
      "s3/${s3_ota_binary}" \
      "esp32/${esp32_binary}" \
      "esp32/${esp32_ota_binary}" > SHA256SUMS
  fi
)

ESPHOME_IMAGE_RESOLVED="${ESPHOME_IMAGE:-${ESPHOME_IMAGE_DEFAULT}}" \
ESPHOME_PLATFORM_RESOLVED="${ESPHOME_PLATFORM:-${ESPHOME_PLATFORM_DEFAULT}}" \
ESPHOME_MANIFEST_DIGEST_RESOLVED="${ESPHOME_MANIFEST_DIGEST:-${ESPHOME_MANIFEST_DIGEST_DEFAULT}}" \
python3 - "${repo_dir}" "${output_dir}" "${version}" <<'PY'
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
from urllib.parse import quote

repo, output, version = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
oid = subprocess.check_output(["git", "-C", repo, "rev-parse", "HEAD"], text=True).strip()
dirty = subprocess.run(
    ["git", "-C", repo, "diff", "--quiet", "HEAD", "--", ":(exclude)release/public"],
    check=False,
).returncode != 0
epoch = int(os.environ["SOURCE_DATE_EPOCH"])
artifacts = []
for line in (output / "SHA256SUMS").read_text().splitlines():
    sha256, relative = line.split(maxsplit=1)
    path = output / relative
    artifacts.append({
        "path": relative,
        "size": path.stat().st_size,
        "sha256": sha256,
        "md5": hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest(),
    })
metadata = {
    "schema_version": 1,
    "version": version,
    "source_oid": oid,
    "source_dirty": dirty,
    "source_date_epoch": epoch,
    "built_at": dt.datetime.fromtimestamp(epoch, dt.timezone.utc).isoformat().replace("+00:00", "Z"),
    "toolchain": {
        "esphome": os.environ["ESPHOME_IMAGE_RESOLVED"],
        "platform": os.environ["ESPHOME_PLATFORM_RESOLVED"],
        "resolved_manifest_digest": os.environ["ESPHOME_MANIFEST_DIGEST_RESOLVED"],
    },
    "artifacts": artifacts,
}
(output / "build-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
components = [
    {"type": "file", "name": item["path"], "version": version,
     "bom-ref": f"artifact:{item['path']}",
     "hashes": [{"alg": "SHA-256", "content": item["sha256"]}]} for item in artifacts
]
image = os.environ["ESPHOME_IMAGE_RESOLVED"]
image_name, image_digest = image.rsplit("@sha256:", 1)
components.append({
    "type": "container", "name": image_name, "version": "2026.7.0",
    "bom-ref": f"container:{image}", "hashes": [{"alg": "SHA-256", "content": image_digest}],
    "purl": "pkg:oci/esphome@2026.7.0?repository_url=ghcr.io/esphome",
    "properties": [{"name": "passion-wave:container-platform",
                    "value": os.environ["ESPHOME_PLATFORM_RESOLVED"]},
                   {"name": "passion-wave:resolved-manifest-digest",
                    "value": os.environ["ESPHOME_MANIFEST_DIGEST_RESOLVED"]}],
})

def lock_components(path):
    values = {}
    current = None
    in_dependencies = False
    for line in path.read_text().splitlines():
        if line == "dependencies:":
            in_dependencies = True
            continue
        if line.startswith("direct_dependencies:"):
            break
        if not in_dependencies:
            continue
        if line.startswith("  ") and not line.startswith("    ") and line.endswith(":"):
            current = line.strip()[:-1]
            values[current] = {"version": "unknown", "hash": None}
        elif current and line.startswith("    version:"):
            values[current]["version"] = line.split(":", 1)[1].strip().strip("'\"").replace("*", "unknown")
        elif current and line.startswith("    component_hash:"):
            values[current]["hash"] = line.split(":", 1)[1].strip()
    return values

dependencies = {}
for role in ("passion_wave_factory_s3", "passion_wave_factory_esp32"):
    lock = repo / "esphome/.esphome/build" / role / "dependencies.lock"
    if lock.is_file():
        dependencies.update(lock_components(lock))
for name, item in sorted(dependencies.items()):
    component = {
        "type": "library", "name": name, "version": item["version"],
        "bom-ref": f"component:{name}@{item['version']}",
        "purl": f"pkg:generic/{quote(name, safe='')}@{quote(item['version'], safe='')}",
        "properties": [{"name": "passionwave:source", "value": "ESP-IDF dependencies.lock"}],
    }
    if item["hash"]:
        component["hashes"] = [{"alg": "SHA-256", "content": item["hash"]}]
    components.append(component)
external_yaml = (repo / "esphome/rotaryknob-s3-ui-core.yaml").read_text()
external_ref = "214077a1934e5a1f52488731bf45ab51048c3570"
if external_ref not in external_yaml:
    raise SystemExit("Pinned drv2605 external component ref is missing")
components.extend([
    {
        "type": "library", "name": "RAR/esphome-drv2605", "version": external_ref,
        "bom-ref": f"git:RAR/esphome-drv2605@{external_ref}",
        "purl": f"pkg:github/RAR/esphome-drv2605@{external_ref}",
    },
    {
        "type": "application", "name": "xtensa-esp-elf", "version": "14.2.0_20260121",
        "bom-ref": "toolchain:xtensa-esp-elf@14.2.0_20260121",
        "purl": "pkg:generic/xtensa-esp-elf@14.2.0_20260121",
    },
])
application_ref = f"device:passion-wave@{version}"
sbom = {
    "bomFormat": "CycloneDX",
    "specVersion": "1.6",
    "serialNumber": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, f'passion-wave:{oid}:{version}')}",
    "version": 1,
    "metadata": {
        "timestamp": dt.datetime.fromtimestamp(epoch, dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "component": {"type": "device", "name": "PassionWave RotaryKnob", "version": version,
                      "bom-ref": application_ref},
        "tools": {"components": [{"type": "application", "name": "PassionWave deterministic builder",
                                  "version": oid}]},
    },
    "components": components,
    "dependencies": [{"ref": application_ref,
                      "dependsOn": [item["bom-ref"] for item in components]}],
}
(output / "sbom.cdx.json").write_text(json.dumps(sbom, indent=2) + "\n")
PY

for relative in \
  "s3/${s3_binary}" "s3/${s3_ota_binary}" \
  "esp32/${esp32_binary}" "esp32/${esp32_ota_binary}"; do
  if [[ -f "${final_output_dir}/${relative}" ]] &&
      ! cmp -s "${final_output_dir}/${relative}" "${output_dir}/${relative}"; then
    echo "Immutable artifact already exists with different bytes: ${relative}; bump VERSION." >&2
    exit 8
  fi
done

echo "Public release artifacts: ${output_dir}"

backup_dir="${output_parent}/.${output_name}.backup.$$"
if [[ -e "${final_output_dir}" ]]; then
  mv "${final_output_dir}" "${backup_dir}"
fi
if mv "${output_dir}" "${final_output_dir}"; then
  [[ ! -e "${backup_dir}" ]] || rm -rf "${backup_dir}"
else
  [[ ! -e "${backup_dir}" ]] || mv "${backup_dir}" "${final_output_dir}"
  exit 1
fi
output_dir="${output_parent}/.${output_name}.promoted.$$"
echo "Atomically promoted public release artifacts: ${final_output_dir}"
