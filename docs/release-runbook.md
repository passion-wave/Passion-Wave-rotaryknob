# Coordinated release and device rollout runbook

This is the canonical maintainer process for one coordinated PassionWave
release. It covers the Home Assistant integration, ESP32 Bridge firmware,
ESP32-S3 display firmware, public installer, HACS delivery and physical rollout.

## 1. Release contract

One RotaryKnob contains two independently updated processors but exposes one
customer-facing firmware transaction. Every coordinated release uses one
SemVer prerelease such as `3.0.1-beta.6` across:

- repository `VERSION`;
- all factory, managed and shared ESPHome project versions;
- `custom_components/passion_wave/const.py`;
- the Home Assistant manifest form, for example `3.0.1b6`;
- public manifests, firmware filenames, website, tags and release notes.

The integration is always installed before device firmware. Firmware updates
always run Bridge first, wait for its Native API reconnect, then update S3 and
wait for its reconnect. Never publish a stable manifest before every referenced
immutable OTA asset is reachable.

## 2. Repositories and ownership

| Repository | Owns |
| --- | --- |
| `Passion-Wave-rotaryknob` | Integration, both firmware cores, six build profiles, tests, public binary source and technical documentation |
| `Passion-Wave-web` | Browser installer, same-origin firmware proxy, public manifests and production deployment |
| `Passion-Wave-control` | Cross-repository governance, launch status and remaining gates |

Read each repository's `AGENTS.md` before editing. Preserve user-owned dirty or
untracked files. Never place Wi-Fi, API, OTA, HACS or Home Assistant credentials
in tracked files, logs, commit messages or release notes.

## 3. Preflight and baseline evidence

1. Fetch and inspect all repositories without discarding local changes:

   ```bash
   git status --short --branch
   git fetch --prune
   git log --oneline --decorate -5
   ```

2. Confirm tools: Git, GitHub CLI, Docker, `jq`, Node.js 22+, `npm`, `curl`,
   `shasum` and reachable Home Assistant.
3. Confirm `HOME_ASSISTANT_TOKEN` is present without printing it. Set the base
   URL separately, for example `HA_BASE_URL=http://homeassistant.local:8123`.
4. Capture the pre-update state for every target product:
   - logical update entity;
   - Bridge/S3 installed versions and connectivity;
   - selected media player state, title, artist and cover;
   - rendered title and runtime presentation diagnostics;
   - startup and protocol-error diagnostics relevant to the change.
5. Record which physical checks cannot be inferred remotely, such as display
   seams, color corruption, touch feel, haptics or audible playback.

## 4. Implementation and regression tests

Add the smallest regression test that fails for the defect before or together
with the fix. Keep authoritative state ownership explicit: Home Assistant owns
selected player metadata, Bridge owns external I/O, and S3 owns rendering.

Run fast tests during iteration:

```bash
docker run --rm -e PYTHONPATH=/work -v "$PWD":/work -w /work \
  ghcr.io/home-assistant/home-assistant:2026.8.2 pytest -q tests
./tools/config.sh esphome/managed-test-s3.yaml
./tools/build.sh esphome/managed-test-s3.yaml
```

For image changes, inspect source dimensions and at least one representative
asset visually. Avoid runtime scaling of embedded RGB565 artwork; prepare its
final overscan dimensions before ESPHome converts it.

## 5. Version and release documentation

Update all version surfaces together. Search for the previous version outside
historical immutable manifests:

```bash
rg -n 'PREVIOUS_VERSION' --glob '!release/public/**' .
```

Update `README.md`, `RELEASE.md`, `docs/known-issues.md`, affected architecture
documents and this runbook when the process itself changes. `RELEASE.md` must
state the root cause, customer-visible behavior, automated evidence, artifact
hashes and exact live-acceptance gates. Do not claim a physical visual check
until it was observed on hardware.

## 6. Full integration and firmware qualification

The standard one-command qualification is:

```bash
./tools/qualify-release.sh release/public
```

It performs:

1. version-contract and whitespace checks;
2. the complete test suite in Home Assistant 2026.7.4 and 2026.8.2 in parallel;
3. validation of Factory S3, Factory Bridge, Managed production S3/Bridge and
   Managed test S3/Bridge;
4. compilation of all four managed profiles;
5. factory compilation and assembly of both Factory and OTA binaries;
6. JSON, version and SHA-256 verification of public manifests and artifacts.

The expected public set is:

```text
release/public/SHA256SUMS
release/public/s3/manifest-<version>.json
release/public/s3/manifest.json
release/public/s3/passion-wave-rotaryknob-s3-<version>.factory.bin
release/public/s3/passion-wave-rotaryknob-s3-<version>.ota.bin
release/public/esp32/manifest-<version>.json
release/public/esp32/manifest.json
release/public/esp32/passion-wave-rotaryknob-esp32-<version>.factory.bin
release/public/esp32/passion-wave-rotaryknob-esp32-<version>.ota.bin
```

Copy the final four hashes into `RELEASE.md` only after this build. Run
`git diff --check` and inspect the staged paths before committing.

## 7. Firmware and integration publication

1. Create a feature branch from current `main`.
2. Stage only reviewed source, documentation, versioned manifests and the four
   intended binaries. Never stage caches or unrelated untracked manifests.
3. Commit, push and open one draft PR. Wait for all repository checks, mark it
   ready and merge only when green.
4. Pull merged `main` and use its full commit OID as release target.
5. Create `v<version>` with `RELEASE.md`, four binaries and `SHA256SUMS`.
6. Create immutable `v<version>-assets` at the same merged commit because the
   website Worker streams only allowlisted files from that tag.
7. Verify GitHub-reported asset sizes and SHA-256 digests.

Do not upload the two same-named chip manifests as release assets; they collide
by basename. They remain available in the source/tag and website.

## 8. Website import and production verification

In `Passion-Wave-web`:

1. bump `VERSION`, `package.json`, `package-lock.json`, pages and release notes;
2. prepend all four new immutable asset routes in `worker.js`, retaining older
   versions for rollback;
3. import the qualified firmware set:

   ```bash
   tools/import-firmware.sh /absolute/path/to/Passion-Wave-rotaryknob/release/public
   npm run build
   npm run validate
   ```

4. run local Wrangler and download both OTA paths through the same-origin proxy;
5. compare both downloaded SHA-256 values with firmware `SHA256SUMS`;
6. publish through one draft PR, wait for GitHub and Cloudflare checks, merge,
   and create the matching web tag/release;
7. wait for the production Worker check, then verify both stable manifests and
   both production OTA hashes with a cache-busting query parameter.

## 9. HACS integration rollout

Use the reusable skill helper rather than rewriting WebSocket messages. It
authenticates with `HOME_ASSISTANT_TOKEN`, never prints the token and supports:

```bash
python scripts/ha_release.py hacs-info --repository-id <id>
python scripts/ha_release.py hacs-refresh --repository-id <id>
python scripts/ha_release.py hacs-install --repository-id <id> --version v<version>
python scripts/ha_release.py restart
python scripts/ha_release.py wait-core
```

The helper requires `aiohttp`; execute it inside a pinned Home Assistant
container when it is unavailable on the host. Refresh the HACS repository
explicitly so a newly published GitHub tag is not hidden by cached metadata;
`hacs-install` performs this refresh and verifies both offered and installed
versions. After restart, wait for Core state `RUNNING`, not merely a responding
HTTP socket. Confirm the local custom integration manifest and HACS
`installed_version` both match the release.

## 10. Device rollout through Home Assistant

Roll out one physical device at a time. For each logical update entity:

1. call `homeassistant.update_entity` and require the new `latest_version`;
2. call `update.install` with only `entity_id`, exactly matching the UI path;
3. monitor state, percentage, phase, both installed versions, both transport
   statuses and `last_error` until completion;
4. expect Bridge progress first, then S3; a long 50-percent interval while the
   blocking S3 action runs is valid;
5. require final state `off`, `phase=complete`, both processors on the target,
   both connected and `last_error=null`;
6. refresh the entity once more and confirm no update remains.

Never start the second product while the first transaction is active. Do not
use the hidden technical ESPHome updates except for documented recovery.

## 11. Live acceptance

After each two-processor reboot verify without manual integration reload:

- player, runtime title, rendered title, artist and cover represent one current
  presentation;
- idle metadata is rehydrated and does not fall back to `Keine Wiedergabe`;
- Bridge/S3 API and UART connectivity recover without protocol errors;
- UI and valid clock appear before the screensaver timeout;
- the changed feature is exercised physically on every installed device.

For media-transition changes, run at least five next-track transitions and
compare media page, cover screensaver and Home Assistant diagnostics. For image
changes, inspect every edge and representative light/dark artwork directly on
both displays. Record results in `docs/known-issues.md` immediately.

## 12. Recovery and rollback

- If HACS is newer but firmware is not offered, refresh the logical entity and
  verify public manifests before touching device registrations.
- If one ECU fails, preserve the successful ECU, inspect its transport status
  and retry only through the logical transaction when safe.
- If the logical path cannot recover, use the matching hidden ESPHome endpoint
  or USB Factory image for that chip only.
- Never flash an S3 binary to Bridge or a Bridge binary to S3.
- Roll back with immutable versioned artifacts; never move an existing asset
  tag or replace a published binary.

## 13. Completion record

A release is complete only when source PRs, immutable releases, production
manifests, HACS state, both processors of every requested product and physical
acceptance are accounted for. Final reporting must distinguish automated,
remote live and directly observed visual evidence.
