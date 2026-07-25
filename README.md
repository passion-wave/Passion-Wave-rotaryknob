# Passion Wave Rotaryknob

Firmware and Home Assistant integration for the round JC3636K518C controller
with an ESP32-S3 display processor and an ESP32 coprocessor.

Current coordinated release: **2.0.0 — `responsiveness,nextUI`**.

Version 2.0.0 preserves the 1.2.0 functional baseline while promoting the
two-processor performance architecture, NextUI and the ungeflashed-device
factory pipeline. Historical migration revisions remain documented for
traceability.

Version 2.0 is now integrated into `main`. The former integration branch
`feature/next` is retained at the same release commit; `stable/1.2.0` remains
the unchanged rollback branch.

## Current architecture

- ESP32-S3: EC1 encoder, touch, LVGL rendering, haptics, local optimistic UI and
  a compatibility network path.
- ESP32: Home Assistant API actions/state, weather, Music Assistant library,
  radar/floorplan/network assets and EC2 diagnostics.
- Inter-processor link: 2 Mbit/s framed UART with COBS, CRC, priorities,
  acknowledgements and bounded payloads.
- Home Assistant: optional automation blueprints for device targets and Music
  Assistant library paging.

Both processors retain independent OTA update paths. The S3 compatibility path
must remain enabled until the final recovery and endurance gates are passed.

## Repository layout

- `esphome/`: firmware profiles, local C++ components and assets.
- `home_assistant/blueprints/`: Home Assistant automation blueprints.
- `home_assistant/packages/`: advanced optional YAML packages.
- `home-assistant/pyscript/`: advanced floorplan renderer; this legacy
  directory name is scheduled for consolidation.
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

## Installation status

The repository now supplies separate credential-free S3 and ESP32 factory
profiles, reproducible release artifacts and independent OTA paths. The public
browser flow lives in `Passion-Wave-web`; private test credentials remain only
in the development wrappers. Maintainers should follow
[Installation](docs/installation.md) and
[Unflashed customer onboarding](docs/unflashed-customer-onboarding.md).

## Home Assistant

The current blueprints use typed Home Assistant selectors:

- [Dynamic targets](home_assistant/blueprints/automation/passion_wave/rotaryknob_device_defaults.yaml)
  selects one media player and four light entities.
- [Music Assistant library bridge](home_assistant/blueprints/automation/passion_wave/rotaryknob_music_assistant_library.yaml)
  provides bounded, paged playlist, radio, podcast and track data.

These blueprints are useful for development, but the final customer product
should use a Home Assistant integration with a config flow so buyers never
copy entity IDs, MQTT credentials or YAML.

## Documentation

- [Version 2.0 release](RELEASE.md)
- [Onboarding ungeflashter Verkaufsgeräte](docs/unflashed-customer-onboarding.md)
- [Project review](docs/project-review.md)
- [Customer product architecture](docs/customer-product-architecture.md)
- [Dual-MCU performance framework](docs/dual-mcu-performance-framework.md)
- [Dual-MCU Home Assistant bridge](docs/dual-mcu-ha-bridge.md)
- [UI Next framework](docs/ui-next-framework.md)
- [Migration roadmap](docs/final-migration-roadmap.md)
- [Test installation](docs/dual-mcu-test-installation.md)
- [Responsiveness test catalog](docs/stage1-responsiveness-test-catalog.md)
- [End-to-end latency benchmark](docs/end-to-end-latency-benchmark.md)
- [UX assurance report](docs/ux-assurance-report.md)
- [Debugging](docs/debugging.md)

## License

MIT. See [LICENSE](LICENSE).
