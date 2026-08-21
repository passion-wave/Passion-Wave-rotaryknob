# Firmware build pipeline

This document owns the repository-local build and qualification behavior. The
cross-repository entrypoint, version contract and final receipt live in
`Passion-Wave-control`. Publication and live-device mutation remain in
[the release runbook](release-runbook.md).

## Fast local feedback

Run only the affected ownership boundary:

```sh
tools/fast-check.sh --scope integration
tools/fast-check.sh --scope s3
tools/fast-check.sh --scope bridge
tools/fast-check.sh --scope integration,s3
```

The integration scope runs the current Home Assistant container. S3 and Bridge
each validate Factory, Managed Production and Managed Test configuration, then
compile one representative Factory profile. `--scope all` covers all three
areas. Containers are digest-pinned in `tools/release-toolchain.env`; build and
PlatformIO caches are local and never release evidence. Candidate builds derive
`SOURCE_DATE_EPOCH` from the Git commit. ESPHome 2026.7.0 does not apply it to
generated build metadata, so `tools/esphome-deterministic.py` narrowly
normalizes that metadata without replacing the process clock. Deterministic
builds mount the persistent ESPHome dependency cache explicitly. The local
double-build proof shares those read-only inputs but disables ccache, ensuring
that both payload sets are compiled independently.

Normal fast and Beta builds mount `.esphome_cache/ccache` into every ESPHome
container as `/root/.ccache`. Managed Production, Managed Test and Factory
therefore reuse identical compiler outputs within one runner instead of
recompiling the shared product sources. RC reproducibility keeps
`CCACHE_DISABLE=1`; cache contents are never receipt or artifact evidence.

On a cold runner the managed production S3 endpoint compiles first and
initializes the shared ESP-IDF Python environment. Only after it succeeds do
the remaining three managed endpoints compile in parallel. This keeps the
parallel speedup without allowing first-use ESP-IDF cleanup races in a shared
`.esphome` tree.

After the four managed endpoints pass, their generated build directories are
removed by a short-lived container before the public Factory/OTA assembly
starts. Container-side deletion is intentional because ESPHome's generated
files are root-owned on Linux runners. The cleanup names exactly the four
managed build directories and cannot widen to the repository or build root.
CI caches dependency downloads only, never `esphome/.esphome` build output.
This bounds fresh-runner disk use and prevents a late Factory CMake failure
after an otherwise valid managed matrix.

The qualified Beta/RC path then builds Factory S3 and Factory Bridge in
parallel. This mode is enabled only after the managed S3 warmup has initialized
ESP-IDF; direct standalone public builds remain serial and cold-start safe.
Both child statuses are collected before artifact assembly, so one failed
factory target cannot be hidden by the other target succeeding.

GitHub Actions computes its ESPHome cache key once, before compilation, from
the tracked Git index entries below `esphome`, `custom_components`, `assets`
and `tools` plus `VERSION`. Generated `.esphome` trees never participate in the
key and therefore cannot break the post-job cache phase or invalidate an
otherwise identical source build.

## Candidate qualification

The normal command is issued from the Control repository:

```sh
tools/release build --channel alpha --version X.Y.Z-alpha.N
tools/release build --channel beta  --version X.Y.Z-beta.N
tools/release build --channel rc    --version X.Y.Z-rc.N
```

The orchestrator calls this repository's local gate:

```sh
tools/qualify-release.sh --channel beta \
  --output release/public \
  --log-dir .release-pipeline/logs
```

| Gate | Alpha | Beta | RC |
| --- | ---: | ---: | ---: |
| SemVer/PEP440, secret and whitespace contracts | yes | yes | yes |
| Home Assistant current version | yes | yes | yes |
| Home Assistant baseline version | no | yes | yes |
| Six ESPHome configuration validations | yes | yes | yes |
| Two Factory compiles and four public binaries | yes | yes | yes |
| Four Managed endpoint compiles | no | yes | yes |
| Two clean-worktree Factory builds, 4/4 equal hashes | no | no | yes |
| Physical clean install/update/rollback | prohibited | limited test devices | required before promotion |

Alpha optimizes feedback time, not release confidence. Beta is the complete
automated product matrix. RC adds reproducibility and requires a clean tracked
tree; a remote runner and the physical matrix remain explicit manual gates in
the receipt.

The manual `RC two-runner reproducibility` GitHub workflow performs the same
Factory build on two fresh hosted runners and accepts only 4/4 bit-identical
payload hashes. Each job starts with an absent build tree and `CCACHE_DISABLE=1`;
the cache contains dependency downloads only. The compare job also requires
identical source OID, epoch, toolchain and artifact metadata. That green workflow is mandatory RC evidence; the local
clean-worktree double build gives faster preflight feedback but does not
replace it.

## Atomic artifacts

`tools/build-public-release.sh` builds into a sibling staging directory while
the previous `release/public` remains untouched. It validates manifests and
`SHA256SUMS`, then swaps the complete tree under a process lock. On any failure
the last good target remains byte-identical. Historical versioned binaries are
copied into staging and retained; only stable manifests and the current hash
inventory advance. If the same version already exists with different candidate
bytes, exit `8` preserves the tree and requires a version bump.

The four candidate payloads are:

```text
s3/passion-wave-rotaryknob-s3-{version}.factory.bin
s3/passion-wave-rotaryknob-s3-{version}.ota.bin
esp32/passion-wave-rotaryknob-esp32-{version}.factory.bin
esp32/passion-wave-rotaryknob-esp32-{version}.ota.bin
```

The Control receipt records SHA-256, OTA/transport MD5, size, three Git OIDs,
dirty state, digest-pinned toolchains, gate durations, the web URL rewrite and
hash evidence for the deployed manifests, Worker map and complete Web `dist/`
tree.
Promotion never compiles again; it accepts only those recorded hashes.
The artifact tree also carries `build-metadata.json` and a CycloneDX
`sbom.cdx.json`. Its dependency inventory includes all components from both
ESP-IDF `dependencies.lock` files, the ESPHome image digest, compiler, pinned
external component and four payloads. GitHub's candidate workflow attests the
binary set, while the pinned Gitleaks action scans repository history.

## Cache, resume and token budget

Each gate hashes only its declared inputs plus command and toolchain contract.
Successful expensive gates are reused only when both input fingerprint and
declared outputs still match. Full logs are persisted by run and the console
shows one line per gate. A failed run resumes with:

```sh
tools/release build --channel beta --version X.Y.Z-beta.N --resume
```

Use `--from GATE` only for audited recovery. `--force GATE` and dirty candidate
runs require `--reason`; dirty Beta/RC receipts are never promotable. Agents
should read only Control `.release-pipeline/SUMMARY.md` or
`release-status.json`, not replay all logs.

## Failure recovery

| Exit | Meaning | Recovery |
| ---: | --- | --- |
| 2–3 | metadata/tool/version contract | fix the named contract; rerun plan/check |
| 4–7 | test, compile, artifact or reproducibility gate | inspect only the named log tail; fix source; use `--resume` |
| 8 | existing version would receive different bytes | preserve immutable files; bump `VERSION` through Control |
| 75 | another build/import holds the lock | wait for it or verify the owning process; never delete an active lock |

`tools/test-release-atomicity.sh` injects a failed compiler command into a
temporary last-good tree and is required in CI. The gate passes only if the
sentinel hash is unchanged and no partial output is promoted.

Clean CI checkouts have no private `esphome/secrets.yaml`. Fast and full gates
therefore copy `secrets.example.yaml` to both ESPHome include locations only
when no real root secret exists, and remove only their own copies through an
exit trap. A maintainer's existing secret is never overwritten, supplemented
or deleted.

Never move an existing tag, replace an immutable binary or point a stable
manifest at an asset that has not been fetched and hash-verified.
