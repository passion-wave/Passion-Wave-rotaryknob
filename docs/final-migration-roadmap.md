# Final migration roadmap

This roadmap records the four dual-MCU migration milestones. The current
product release is Version `2.1.0` (`reliable-onboarding,responsiveness`); internal S3
`.98` and ESP32 `.50` counters plus `.80/.39` and `.89/.45` in the milestone
history are rollback checkpoints. The production device
`passion_wave_rotaryknob` remains unchanged on version 1.2.0.

The target split is:

- ESP32-S3: EC1, touch, display, LVGL, haptics, battery protection and immediate
  local feedback;
- classic ESP32: Wi-Fi-facing Home Assistant, Music Assistant, MQTT and HTTP
  work, caches, retries and reconnect snapshots;
- UART: bounded binary state, action and streamed-asset transport;
- S3 Wi-Fi/API/OTA: rescue and maintenance only, not part of normal feature
  execution.

## Milestone 1: Stabilize the current baseline

Freeze feature work briefly and qualify `.80` / `.39` as the last compatibility
baseline.

Scope:

- verify playlist and track pagination at offsets 0, 16, 32, 48 and the
  64-entry device limit;
- verify cold start, S3-only restart, ESP32-only restart and Home Assistant
  restart;
- run the encoder, volume, media-start and end-to-end latency probes;
- exercise radar, cover changes, forecast, lighting and media paging together;
- add a repeatable pagination diagnostic so page gaps, request generations,
  loaded counts and processor resets are visible without attaching permanent
  log streams;
- complete a 24-hour mixed-load run with no increasing UART/encoder errors,
  unplanned fallback or reset.

Exit gate:

- every functional block of 1.2.0 remains available;
- active input p99 stays below 25 ms;
- page loading always reaches either a completed count or an explicit error;
- both processors remain independently OTA-recoverable.

Rollback point: `.80` / `.39` and the matching mounted ESPHome configuration.

## Milestone 2: Complete network and asset ownership

Move all remaining normal-operation network work to the classic ESP32 in one
coherent data-plane release.

Scope:

- stream media artwork bytes through the ESP32 instead of downloading them on
  the S3;
- migrate the remaining light details: light-1 colour temperature and legacy
  light-4 preset/RGB state;
- migrate current-weather precipitation probability;
- replace the direct S3 radar rescue URL with the existing acknowledged ESP32
  radar stream;
- proxy the photo-slideshow and house-floorplan assets so their full-screen
  views no longer require S3 HTTP;
- provide bounded caches, readiness flags, timeouts, CRC checks, reconnect
  snapshots and an explicit error result for every new route;
- keep control and encoder frames ahead of all bulk image chunks.

Exit gate:

- the inventory reports 32 of 32 Home Assistant states mirrored by the ESP32;
- all five S3 image consumers receive their data without normal S3 HTTP;
- repeated image changes cannot create an active scheduler gap above 25 ms;
- loss of one asset never blocks navigation, encoder processing or OTA.

Rollback point: one feature-group switch re-enables the existing S3
compatibility implementation while keeping the same UI.

Implementation status (`.89` / `.45`):

- all 32 Home Assistant values have an ESP32-owned mirror;
- the final five routes are current precipitation probability, light-1 colour
  temperature, light-4 RGB, light-4 legacy preset and radar-image path;
- one acknowledged CRC32 asset transport now carries radar, media cover, three
  slideshow images and the house floorplan;
- only one bounded compressed asset is in flight; the newest pending request
  wins and encoder/control frames retain control priority;
- the S3 decodes bytes on its non-UI core only after active input has been
  quiet for 100 ms; LVGL state changes remain on the main loop;
- Music Assistant artwork is normalized to its smallest supported 256-pixel
  source on the ESP32. In the live test this reduced the compressed transfer
  from 134,386 to 41,808 bytes and decode time from 1,589 to 413 ms; the UI
  scheduler gap during decode was 10 ms;
- a link loss cannot release the shared PSRAM buffer while the core-0 decoder
  is still consuming it;
- URL, HTTP, size, timeout, CRC and decoder errors are explicit and
  non-blocking;
- healthy-bridge operation starts no S3 image HTTP. The inherited downloader
  remains the bridge-loss rescue path until Milestone 3 removes it.
- after ten seconds of uninterrupted playback and ten seconds without input,
  the intentional full-screen cover page is exposed; leaving it always returns
  to UI Next media rather than the inherited media screen. The primary media
  view reserves its full content width for title and artist;
- the direct-S3 rescue path recognizes both Music Assistant image-proxy URL
  shapes and requests a bounded 256-pixel JPEG.

## Milestone 3: Cut over to the final processor boundary

Remove redundant S3 network consumers after Milestone 2 has passed its gates.

Scope:

- remove all 32 inherited S3 Home Assistant state subscriptions from the test
  overlay;
- keep Home Assistant truth, Music Assistant, MQTT, HTTP, caching and retry
  ownership exclusively on the classic ESP32;
- stop normal S3 MQTT and HTTP activation, including automatic wake-up for a
  merely cold or temporarily busy cache;
- retain S3 native API and OTA for diagnostics and recovery;
- introduce a documented deliberate rescue boot mode that restores the legacy
  S3 network path only when requested, rather than during normal operation;
- verify that ESP32 loss leaves EC1, local pages, clock display, battery
  protection and cached UI usable without accidental commands.

Exit gate:

- normal operation produces no S3 Home Assistant subscription, MQTT or HTTP
  traffic;
- all user commands use exactly one ESP32-owned route;
- reconnect restores a complete state snapshot without restarting the S3;
- deliberate rescue mode and independent OTA work from a cold start.

Rollback point: reinstall the Milestone-2 S3 image; the ESP32 protocol remains
backward compatible for one release.

Implementation step 3A (`.88` / `.45`):

- loss of the ESP32 bridge or a library paging error no longer enables S3 MQTT
  automatically;
- the configuration entity `S3 Network Rescue Mode` is the only activation
  path for the compiled compatibility MQTT/weather/library route;
- Rescue is deliberately non-persistent (`ALWAYS_OFF`) and must be enabled
  again after every S3 reboot;
- disabling Rescue immediately stops S3 MQTT and clears all compatibility
  fallback flags;
- S3 Wi-Fi, encrypted native API, ESPHome OTA and Safe Mode remain available
  at all times; the classic ESP32 retains its own independent encrypted API,
  OTA and Safe Mode;
- both profiles must compile and both TCP OTA endpoints must be reachable
  before an S3 migration image is installed.

Implementation step 3B (`.89` / `.45`):

- radar, slideshow photos, house floorplan and both media-cover targets use the
  acknowledged ESP32 asset stream during normal operation;
- loss of the bridge no longer starts an S3 `online_image` download for any of
  these consumers;
- with Rescue off, missing bridge assets produce an explicit unavailable or
  waiting state and leave navigation and local controls responsive;
- direct S3 HTTP remains compiled only for deliberate Rescue and for the
  unchanged standalone 1.2.0 production profile;
- native S3 API/OTA/Safe Mode and the independent ESP32 API/OTA/Safe Mode are
  unchanged.

Implementation step 3C (Version 2.0 light details):

- WLED preset and Hue scene discovery is owned by the classic ESP32 for all
  four compiled light slots;
- only generation-tagged labels and selection metadata cross to the S3, while
  scene entity IDs and preset values remain in the authoritative ESP32 cache;
- the S3 activates an entry by slot/index, so no arbitrary Home Assistant
  target is accepted from the UI processor;
- direct S3 discovery and actions are limited to standalone or deliberate
  Rescue operation;
- after an isolated S3 reboot, a per-slot completion mask keeps requesting
  snapshots until all four detail catalogs have committed atomically;
- after an ESP32/Home Assistant API reconnect, the authoritative cache is kept
  visible, discovery is deferred by 1.5 seconds and failed response actions are
  retried rather than committed as empty catalogs;
- cover, radar and library transfers share a 16 ms background slot and 4 KiB
  UART buffers, while encoder, touch and state traffic remains immediate;
- ESP32-first/S3-second rolling OTA preserves compatibility and both
  independent recovery routes.

## Milestone 4: Final qualification and release freeze

Treat the processor split as a release candidate rather than continuing with
small migration revisions.

Scope:

- run the complete 1.2.0 regression catalog;
- run 72 hours of mixed media, light, forecast, radar, image and sleep/wake
  load;
- inject ESP32, Home Assistant, Wi-Fi, MQTT and UART interruptions;
- verify zero unplanned page changes, touch-through events, encoder losses,
  resets and growing protocol-error counters;
- measure cold/warm popup, volume, navigation, media start and page-load
  latency;
- freeze protocol/version compatibility, installation steps, rescue procedure,
  rollback images and the production-upgrade checklist.

Exit gate:

- all performance and stability targets pass for 72 hours;
- no normal feature depends on S3 networking;
- a fresh installation and a rollback are reproducible from the documented
  artifacts;
- only then may the architecture be promoted from the second test device to a
  separately approved production revision.

## Immediate next implementation

Feature migration has reached the intended processor boundary. The next step is
Milestone 4 qualification on `.98/.50`: run the complete responsiveness
catalog, verify both OTA and rescue paths from cold boot, then execute the
72-hour mixed-load/failure-injection test. Retail factory profiles and the
two-stage installer are a separate release-engineering stream described in
[Customer product architecture](customer-product-architecture.md).
