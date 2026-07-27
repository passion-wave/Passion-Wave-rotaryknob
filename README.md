# Passion Wave Rotaryknob

Firmware and Home Assistant integration for the round JC3636K518C controller
with an ESP32-S3 display processor and an ESP32 coprocessor.

Current Home Assistant integration beta: **3.0.0-beta.5**. The unchanged
device firmware remains **3.0.0-beta.3 — `secure-zero-psk-pairing`**.

V3 is an intentional breaking architecture release. The obsolete standalone
Single-MCU entrypoint, MQTT media transport, S3 application-network fallback,
All setup blueprints and the YAML media helper have been removed.
Both processors of a physical Rotaryknob must be updated together after the
Home Assistant integration is installed.

## Current architecture

- ESP32-S3: EC1 encoder, touch, LVGL rendering, haptics and local optimistic UI.
- ESP32: Home Assistant API actions/state, weather, Music Assistant library,
  radar/floorplan/network assets and EC2 diagnostics.
- Inter-processor link: 2 Mbit/s framed UART with COBS, CRC, priorities,
  acknowledgements and bounded payloads.
- Home Assistant: the `passion_wave` Custom Integration with a typed Config
  Flow and bounded Music Assistant response services.

Both processors retain independent OTA update paths. The S3 network surface is
limited to provisioning, encrypted ESPHome Native API and OTA. All application
state, commands and network assets are transported by the Bridge and framed
UART. MQTT is not compiled into either role.

## One device, two chips

The product term **Rotaryknob** always means one physical device. It contains
two chips and therefore exposes two independently managed ESPHome endpoints:

- the ESP32-S3 display endpoint `PassionWave Rotaryknob`;
- the classic ESP32 bridge endpoint `PassionWave Rotaryknob Bridge`.

The endpoints need separate chip images, API identities and OTA paths, but they
are not separate product devices. They share one release generation and are
operated as one coordinated unit.

## Multi-device compatibility

Multiple physical Rotaryknobs can run the same source and release version. The
repository does not duplicate complete configurations per installation:

- `managed-s3.yaml` and `managed-esp32.yaml` define the two unavoidable
  processor roles.
- `devices/production.yaml` and `devices/test.yaml` contain only the
  location-specific Home Assistant targets and private substitutions.
- `managed-{production,test}-{s3,esp32}.yaml` are thin build and OTA entrypoints
  for the two physical Rotaryknobs in the current test installation.

The S3 and classic ESP32 cannot share one binary because they use different
chips, flash layouts and responsibilities. They do share the same firmware
cores, version and security policy. Each additional Rotaryknob receives its own
PassionWave Config Entry and two unique endpoint identities. See
[Dual-MCU managed deployment](docs/managed-deployment.md).

## Getting Started

The public browser installer delivers **V3.0.0-beta.3** as an explicitly marked
prerelease. Version 2.1.1 remains the rollback tag. The steps below are for
maintainers and beta testers; promotion beyond beta requires the coordinated
hardware acceptance.

1. Use Home Assistant 2026.7 or newer and ESPHome 2026.7. Music Assistant is
   optional, but required for playlist, radio and podcast browsing.
2. Copy `custom_components/passion_wave` into
   `/config/custom_components/passion_wave`, restart Home Assistant and add
   **PassionWave** under **Settings > Devices & services**.
3. Prepare and validate the two configurations for one Rotaryknob:

   ```sh
   ./tools/config.sh esphome/managed-production-s3.yaml
   ./tools/config.sh esphome/managed-production-esp32.yaml
   ./tools/build.sh esphome/managed-production-s3.yaml
   ./tools/build.sh esphome/managed-production-esp32.yaml
   ```

4. Install the matching S3 and Bridge images, provision both chips on the same
   WLAN and confirm their two ESPHome endpoints in Home Assistant. Never mix
   V2 and V3 on the two chips of one device.
5. Add one PassionWave Config Entry for the physical Rotaryknob. Select its
   Display/S3, Bridge registration, Music Assistant instance, player and four
   ordered light positions. The complete Music Assistant library is enabled
   automatically; all assignments and optional visibility filters remain
   available under **Configure**.
6. Verify encoder, touch, media paging, weather, radar, floorplan, UART status
   and both OTA paths with the acceptance list in
   [Managed deployment](docs/managed-deployment.md).

For a second Rotaryknob, repeat steps 4–6 with a second device overlay and a
second PassionWave Config Entry. Detailed factory and recovery instructions
are in [Installation](docs/installation.md).

## Repository layout

- `esphome/`: shared firmware cores, Factory/Managed deployment layers, thin
  installed-endpoint entrypoints, local C++ components and assets.
- `custom_components/passion_wave/`: installable Home Assistant Custom
  Integration, Config Flow and bounded media services.
- `home_assistant/packages/`: advanced optional YAML packages.
- `home_assistant/pyscript/`: advanced floorplan renderer.
- `docs/`: architecture, installation, migration, validation and product plan.
- `tools/`: developer diagnostics and flash helpers.

## Weather screensaver

The S3 firmware contains a complete local image set for all 15 Home Assistant
weather conditions. The ESP32 bridge forwards the condition, while the S3
switches the precompiled RGB565 image without an HTTP request or loading delay.
Unknown states use `partlycloudy` as a deterministic fallback. Source,
provenance, checksums and the exact state mapping are documented in
[Weather screensaver assets](assets/screensaver/README.md).

When the screensaver opens, the display starts at 100% brightness and uses the
native PWM transition engine to fade continuously to 10%. The default fade
duration is five minutes. Home Assistant exposes the persistent configuration
numbers `Screensaver Startverzögerung` (default 30 seconds) and `Screensaver
Abdunkeldauer` (default 300 seconds). The display remains at 10% after the fade;
leaving the screensaver restores the normal 70% UI brightness. The fade does
not add periodic work to the UI loop.
Rotating the encoder while the screensaver is visible raises the backlight to
100% immediately, holds it there for two seconds after the last encoder pulse
and then restarts the configured fade. Rotary input never leaves the
screensaver or reaches a control on the page behind it.

Below 100% battery state, a separate two-stage idle policy dims the display to
10% after 15 seconds, then switches it off after 60 seconds without playback or
180 seconds with playback. Home Assistant exposes all four values as persistent
configuration numbers. The Settings entry `DEV: Wach halten` and the matching
Home Assistant switch disable screensaver, dimming, shutdown and deep sleep for
development sessions.

## Installation status

The repository supplies separate credential-free S3 and ESP32 factory
profiles, reproducible release artifacts, generated chip-specific manifests
and independent OTA paths. A clean factory install erases stale device
identity data and exposes `PassionWave Rotaryknob` plus `PassionWave
Rotaryknob Bridge`. PassionWave uses ESPHome 2026.7's bounded zero-PSK
provisioning path to generate and install an individual API key for each
processor without showing it to the buyer. Authenticated OTA remains part of
the subsequent managed commissioning
step. Private credentials remain only in managed device overlays. Maintainers
should follow
[ESPHome API security lifecycle](docs/api-security-lifecycle.md),
[Installation](docs/installation.md) and
[Unflashed customer onboarding](docs/unflashed-customer-onboarding.md).

## Home Assistant

Copy `custom_components/passion_wave` to Home Assistant's
`/config/custom_components/`, restart Home Assistant and add **PassionWave**
under **Settings > Devices & services**. Create one config entry per physical
Rotaryknob and select:

1. its ESPHome Display/S3 entry;
2. its Bridge entity **PassionWave Integration Entry ID**;
3. the Music Assistant integration instance and player used for browsing and
   playback;
4. zero to four lights in the order shown on the display.

The integration writes only its stable Config Entry ID to the Bridge. Playlist,
radio and podcast rows are not entered manually: they are loaded from the
selected Music Assistant instance. Playlist tracks are sliced in Home Assistant
before crossing the Native API and UART. The UI prefetches the next page with
five entries remaining.

The second Config-Flow step offers searchable multi-select fields for visible
playlists, radio stations and podcasts. **All automatically** remains the
default, so existing entries keep their current behavior. Removing it limits
the device to the selected Music Assistant URIs; an empty selection hides that
category. Ordering and media contents continue to come from Music Assistant.

The integration writes target IDs and friendly names to the selected display
and follows player presentation changes. It also preserves selections when a
target entity is renamed. V3 does not depend on a blueprint, package, MQTT
broker or manually copied encryption key. See
[Native API migration](docs/native-api-migration.md).

## Documentation

- [Cross-repository overview](https://github.com/Passion-Wave/Passion-Wave-control)
- [Version 3.0.0-beta.3 release](RELEASE.md)
- [Known issues and resolved findings](docs/known-issues.md)
- [Onboarding ungeflashter Verkaufsgeräte](docs/unflashed-customer-onboarding.md)
- [Project review](docs/project-review.md)
- [Customer product architecture](docs/customer-product-architecture.md)
- [Dual-MCU performance framework](docs/dual-mcu-performance-framework.md)
- [Dual-MCU Home Assistant bridge](docs/dual-mcu-ha-bridge.md)
- [Radar and floorplan data flow](docs/radar-floorplan-data-flow.md)
- [UI Next framework](docs/ui-next-framework.md)
- [Migration roadmap](docs/final-migration-roadmap.md)
- [Dual-MCU managed deployment](docs/managed-deployment.md)
- [Native API migration](docs/native-api-migration.md)
- [Responsiveness test catalog](docs/stage1-responsiveness-test-catalog.md)
- [End-to-end latency benchmark](docs/end-to-end-latency-benchmark.md)
- [UX assurance report](docs/ux-assurance-report.md)
- [Debugging](docs/debugging.md)

## License

MIT. See [LICENSE](LICENSE).
