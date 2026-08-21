# Firmware and integration 3.0.1-beta.7

Release summary: production pipeline and customer update acceptance

Beta.7 publishes the unchanged Beta.6 media/cover behavior through the new
coordinated production pipeline and creates a real Home Assistant update target
for customer-path acceptance. Runtime version, PEP 440 integration version,
both processor versions and public manifests remain one coordinated release.

## Customer-visible scope

- Home Assistant offers integration `3.0.1b7` before the logical device update.
- Each logical RotaryKnob update remains one transaction: Bridge, confirmed
  reconnect/version, S3, confirmed reconnect/version and final completion.
- The fullscreen 368×368 cover overscan and the atomic title, artist and cover
  presentation from Beta.6 are unchanged.
- The customer acceptance path is now an evergreen, explicit procedure in
  `docs/customer-processes.md`, including persistent progress, single-click
  behavior, restart verification and serial Timo/Marco rollout.

## Build and release changes

- Fresh runners initialize ESP-IDF once, build the remaining managed profiles
  in bounded parallel and remove only known root-owned build trees inside the
  container before Factory assembly.
- Factory S3 and Bridge build concurrently only after the safe warmup; direct
  cold public builds remain serial.
- Dependency caches exclude generated build output and compiler output is
  shared through ccache; RC reproducibility keeps ccache disabled.
- Cross-repository candidates pin exact Firmware and Web OIDs, preserve compact
  failure evidence and never overwrite an immutable versioned artifact.

## Required evidence

The generated Control receipt is authoritative for OIDs, toolchains, gate
durations and all four payload hashes. Promotion additionally requires the
version-specific manual gates: clean install, Timo update, Marco update and
directly observed cover/media behavior. Remote entity state is not visual
evidence.

The pre-update remote baseline on 2026-08-21 is integration, Timo Bridge/S3 and
Marco Bridge/S3 all on `3.0.1-beta.6`, both logical transactions complete and
without a reported error. The customer-agent UI baseline is `BLOCKED` because
no authenticated in-app browser session is available; it is not recorded as a
passed manual gate.
