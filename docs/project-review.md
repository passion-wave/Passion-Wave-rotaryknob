# Project review

Stand: 2026-07-24

## Executive assessment

The project has a strong, responsive dual-MCU runtime and a substantially
complete UI migration. It is suitable for continued test-device development.
It is not yet ready to be sold unflashed to nontechnical customers. The gap is
mainly release engineering and onboarding, not display design.

Current reviewed candidate:

- ESP32-S3: `1.2.0-ui-next.98`
- ESP32: `1.2.0-ha-bridge.50`
- stable compatibility reference: `1.2.0`

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

1. **No complete dual-MCU factory release.** The website has one ESP32-S3
   manifest, while the product requires separate S3 and ESP32 images.
2. **No published sanitized binaries.** Current development profiles depend on
   private Wi-Fi, MQTT, API, OTA and installation-specific entity values.
3. **The physical flash flow is two-stage.** USB-C orientation selects the
   processor. A buyer must flash one processor, unplug, reverse the connector
   and flash the second unless future hardware lets one MCU program the other.
4. **No single logical onboarding flow.** Home Assistant currently sees two
   ESPHome nodes and several supporting automations/packages.
5. **The customer path still needs YAML/MQTT knowledge.** Weather, Music
   Assistant paging, radar and floorplan require developer-level setup.

### High-priority engineering risks

- The S3 compatibility network path has intentionally not been removed; final
  failover, OTA and endurance qualification is still required.
- Music Assistant track paging depends on a separately configured REST command.
  A missing or changed Music Assistant endpoint can leave lists incomplete.
- The public installer documentation previously described a one-processor flow
  and overstated current readiness.
- `home_assistant/` and `home-assistant/` coexist. This is understandable
  historically but error-prone for packaging and support.
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
- S3 build: 2,578,311-byte image, 55.5% DIRAM, 31.7% application partition;
- ESP32 build: 1,135,515-byte image, 41.9% DRAM, 61.9% application partition;
- successful OTA of S3 `.98` to the test device at `192.168.2.101`;
- successful post-OTA API handshake; bridge snapshots resumed and the observed
  scheduler windows were normally 12–17 ms. One startup protocol-error count
  remains visible and must be reset/observed during the qualification catalog.

## Release decision

Do not advertise a one-click retail installation yet. Continue using the
second device as the test target. A retail release becomes credible after:

1. two sanitized factory profiles and signed/hash-verified binaries exist;
2. the web installer guides and verifies both processor stages;
3. one Home Assistant config flow pairs the two nodes and asks only meaningful
   choices;
4. a clean Home Assistant installation passes the no-YAML acceptance test;
5. both OTA paths, rollback and a 72-hour endurance run pass.
