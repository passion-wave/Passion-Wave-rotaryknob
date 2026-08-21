# Firmware and integration 3.0.1-beta.8

Release summary: reproducible firmware assets and production-safe qualification

Beta.8 carries the Beta.7 runtime behavior into a new version because the
immutable Beta.7 asset binaries contained non-reproducible embedded build
times. They are preserved for audit and are not overwritten.

## Customer-visible scope

- Home Assistant integration version is `3.0.1b8`.
- One logical RotaryKnob update still performs Bridge, confirmed reconnect,
  S3, confirmed reconnect and final completion.
- The 368×368 cover overscan and atomic title/artist/cover state remain the
  qualified media behavior introduced before this candidate.

## Build and release changes

- All release binaries bind their build timestamp to the exact source commit
  epoch and must match the coordinated receipt byte for byte.
- Public payload builds delete both exact factory build trees and disable
  ccache, preventing stale timestamp-bearing objects from entering a candidate.
- Managed qualification immediately removes the warmup S3 build tree, then
  runs at most one S3 plus one ESP32 build concurrently and logs free disk
  before and after each group.
- Root-owned generated trees are deleted inside the pinned ESPHome container;
  download/compiler caches remain separate from build output.
- Beta qualification covers two Home Assistant versions, all ESPHome profiles,
  both public payload families, manifests, hashes, SBOM and cross-repository
  distribution.

## Required evidence

Promotion additionally requires physical clean-install, Timo, Marco and
cover/media observations. Remote entity state is useful technical evidence but
does not satisfy a visual gate.
