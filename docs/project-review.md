# Project review

Stand: 2026-07-27

## Executive assessment

The project has a strong, responsive dual-MCU runtime and a substantially
complete UI migration. Credential-free profiles, two release images and the
two-stage website installer now exist. It remains a release candidate rather
than a retail-approved product until clean-device installation, unified
Home Assistant onboarding and the physical endurance gates pass.

Current reviewed candidate:

- product: `3.0.0-beta.1`
- ESP32-S3: managed S3 UI endpoint
- ESP32: managed Home Assistant bridge endpoint
- public installer: `3.0.0-beta.1` prerelease; `2.1.1` rollback

## What is already strong

- The S3 owns the latency-sensitive encoder, touch and rendering path.
- The ESP32 handles Home Assistant work and large/network-derived data.
- UART traffic is framed, checksummed, prioritized and observable.
- Local optimistic UI updates avoid waiting for a network round trip.
- Both processors retain OTA and explicit recovery paths.
- Media lists are bounded and paged instead of copied as unbounded JSON to the
  display processor.
- The UI allocates persistent LVGL objects and updates only changed regions.
- Home Assistant blueprints have source URLs, typed selectors and declared
  minimum versions.

## Findings

### Release blockers

1. **No completed clean-device acceptance.** Both sanitized images and
   chip-specific manifests are published locally and validate successfully,
   but the full two-stage path still needs a physical erased-device run.
2. **The physical flash flow is two-stage.** USB-C orientation selects the
   processor. A buyer must flash one processor, unplug, reverse the connector
   and flash the second unless future hardware lets one MCU program the other.
3. **No single logical onboarding flow.** Home Assistant currently sees two
   ESPHome nodes and several supporting automations/packages.
4. **The complete advanced path still needs YAML knowledge.** Weather, Music
   Assistant paging, radar and floorplan require developer-level setup.

### High-priority engineering risks

- The S3 compatibility network path has intentionally not been removed; final
  failover, OTA and endurance qualification is still required.
- Music Assistant track paging depends on a separately configured REST command.
  A missing or changed Music Assistant endpoint can leave lists incomplete.
- Older control and firmware documents described a one-processor flow and
  understated the implemented two-chip installer. They were corrected on
  2026-07-26.
- `home_assistant/` now contains blueprints, packages and Pyscript together;
  the error-prone duplicate `home-assistant/` source path was removed.
- The migration documents contained historical version numbers presented as
  current state.

### Maintainability and performance risks

- The S3 firmware is a large monolithic YAML plus C++ headers. Product modules
  should be packaged by responsibility and pinned to release tags.
- Current ESPHome warnings include deprecated top-level `online_image`,
  `qspi_dbi`, PlatformIO build flags, ArduinoJson compatibility types and older
  LVGL selector expressions. Clear these before locking the production
  toolchain.
- The `.98` S3 build uses 31.7% of its application partition and 55.5% DIRAM,
  but the reported 16-KB IRAM region is 100% allocated. Treat this as a release
  capacity gate even though the build succeeds.
- Advanced floorplan and radar renderers should be optional capabilities, not
  prerequisites for first setup.

## Changes made by this review

- Enlarged the media-picker Home button from `36×36` to `60×48` pixels and
  moved it away from the round display edge.
- Changed the Music Assistant bridge from `queued` to `parallel` with a limit
  of ten concurrent runs, so a slow track-page request does not block a static
  refresh or a separate page request.
- Replaced trigger-ID template checks with native trigger conditions.
- Added `author` and Home Assistant minimum-version metadata to both
  blueprints.
- Corrected the documentation to distinguish stable firmware, the current test
  candidate and the not-yet-available retail factory release.

## Verification performed

- shell syntax check for all scripts in `tools/`;
- Python byte-code validation for diagnostics and the floorplan renderer;
- local Markdown-link scan;
- repository secret-pattern audit;
- static review of touch targets, blueprint selectors, automation modes,
  firmware profiles and web/control repository hand-off points;
- ESPHome 2026.7.0 compilation of both profiles;
- S3 public factory build: 6,428,167-byte image, 56.0% DIRAM, 79.1% of
  the application partition; 1,698,176 bytes remain in each OTA slot;
- ESP32 public factory build: 1,071,383-byte image, 42.1% DRAM, 58.4% of
  the application partition;
- successful weather-screensaver OTA to the S3 test device;
- successful post-OTA API handshake in 136 ms; bridge snapshots resumed,
  protocol errors remained zero and observed steady scheduler windows were
  normally 13–18 ms.

## Release decision

Do not advertise a one-click retail installation yet. Continue using the
second device as the test target. A retail release becomes credible after:

1. two sanitized factory profiles and signed/hash-verified binaries exist;
2. the web installer guides and verifies both processor stages;
3. one Home Assistant config flow represents the one physical product, binds
   its two technical endpoints and asks only meaningful
   choices;
4. a clean Home Assistant installation passes the no-YAML acceptance test;
5. both OTA paths, rollback and a 72-hour endurance run pass.
