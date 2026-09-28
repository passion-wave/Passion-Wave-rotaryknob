# Firmware and integration 3.0.1-beta.15

Release summary: Fix fullscreen cover fallback, prevent cross-product pairing and add role-specific product naming

## Repository scope

- Role: S3, Bridge and Home Assistant implementation.
- Runtime/channel metadata: `VERSION` and the Control release contract.
- OIDs, toolchain digests, gate durations and payload hashes: generated release receipt.

## Weather avatar feature branch

`codex/feature-weather-avatar-test` uses the coordinated Beta.15 source baseline.
It adds the weather-avatar design assets, both avatar identities and the
implementation plan in `docs/weather-avatar.md`. Firmware, integration and build
sources are unchanged from that baseline; the avatar runtime is not implemented.

This consolidation does not create new firmware binaries or hardware acceptance
evidence. The automated and manual evidence below belongs to the Beta.15 baseline.
Earlier version-mismatch messages in design JSON files remain historical records.

## Automated evidence

- The first compressed cover transfer now prepares both the media-page and
  368×368 fullscreen buffers; fullscreen entry waits for the overscan buffer
  and keeps the page root black.
- Config Flow excludes processors owned by another PassionWave entry, rejects
  stale/live cross-ownership again on submit and confirmation, and shows role,
  MAC/ID and host before saving.
- One product/location name creates the logical, Display and Bridge Home
  Assistant titles, for example `Wohnzimmer_rotaryknob_Display` and
  `Wohnzimmer_rotaryknob_Bridge`.
- Focused onboarding/runtime regression suite: 49 passed. Integration and S3
  fast checks passed before version preparation. The Hosted-CI Beta receipt
  remains the build and publication authority.

## Manual acceptance

Beta.14 Timo evidence established no stale title, artist or cover, no
`Keine Wiedergabe`, and a seam-free real cover. Beta.15 still requires direct
Timo verification of the note-fallback/fullscreen transition and the revised
name/pair confirmation flow. Marco is physically inaccessible and remains an
open independent device gate. Remote entity state is not visual evidence.
