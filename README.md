# Passion Wave Rotaryknob

Passion Wave Rotaryknob is an ESPHome/LVGL firmware blueprint for a round
ESP32-S3 touch display with rotary encoder and haptic feedback. It turns the
device into a compact Home Assistant controller for media, lights, weather,
timer, alarm, rain radar and visual screensavers.

The firmware exposes the important runtime choices directly as persistent Home
Assistant device configuration entities:

- Media entity ID and label
- Light slot 1 entity ID and label
- Light slot 2 entity ID and label
- Light slot 3 entity ID and label
- Light slot 4 entity ID and label
- Rotary haptic effect
- Timer done haptic effect
- Screensaver timeout
- Offline demo mode

The recommended Home Assistant blueprint shows normal entity pickers for all
available `media_player` and `light` entities, writes the selected targets into
the device and mirrors the selected media player's runtime state, title, artist
and cover URL so the Play/Pause icon and cover screensaver work with dynamic
media targets.

Without the blueprint, the firmware still supports dynamic media targets stored
in the device text entity. It polls Home Assistant through `homeassistant.action`
and a `response_template` to read Play/Pause state, title, artist, volume,
progress and cover URL for the selected `media_player`. The blueprint is only a
convenient entity-picker helper.

If the device starts without Wi-Fi, it automatically switches into an offline
promo demo mode after a short timeout. The UI then uses local demo values for
weather, lights and media browsing, while Home Assistant, MQTT and network image
requests stay inactive. The `scrollwheel Demo` setting controls whether this
offline demo is allowed. As soon as Wi-Fi is available again, demo mode is
cleared and the normal Home Assistant integration resumes.

## Repository Layout

- `esphome/`: ESPHome firmware and required local include files.
- `home_assistant/blueprints/`: optional Home Assistant automation blueprints.
- `home_assistant/packages/`: optional rain radar package.
- `docs/`: installation and integration documentation.
- `tools/`: local build and flash helpers.

## Hardware Target

- ESP32-S3 board with 16 MB flash and PSRAM.
- JC3636K518C round 360 x 360 QSPI display.
- CST816 touch controller.
- DRV2605 haptic driver with LRA motor.
- Rotary encoder connected to `GPIO7` and `GPIO8`.
- Backlight PWM on `GPIO47`.
- Battery measurement on `GPIO1`.

## Quick Install

1. Copy the files from `esphome/` into your ESPHome configuration directory.
2. Add your Wi-Fi, MQTT and API secrets.
3. Compile and flash `passion-wave-rotaryknob.yaml`.
4. Import the Home Assistant blueprint from
   `home_assistant/blueprints/automation/passion_wave/rotaryknob_device_defaults.yaml`
   and create one automation from it.
5. Select the ESPHome Rotaryknob device, one media player and four light slots.
   Home Assistant automatically lists the compatible entities.
6. For playlist, radio and podcast rows, publish Music Assistant library data to
   the documented MQTT topics, or import
   `home_assistant/blueprints/automation/passion_wave/rotaryknob_music_assistant_library.yaml`.
   The bridge keeps retained bootstrap payloads small and serves larger
   playlist/track lists through paged MQTT requests.

For showrooms, events or travel, the device can be powered without Wi-Fi. It
will enter promo demo mode and remain locally usable until a known network is
found.

See [docs/installation.md](docs/installation.md) for the complete setup and
[docs/automated-installation.md](docs/automated-installation.md) for the
customer-facing browser install concept.
The touch and rotary safety audit is documented in
[docs/ux-assurance-report.md](docs/ux-assurance-report.md).
Crash and media-selection diagnostics are documented in
[docs/debugging.md](docs/debugging.md).

## Current Blueprint Scope

This repository provides an ESPHome firmware blueprint and an optional Home
Assistant automation blueprint. ESPHome owns the runtime UI and service calls;
Home Assistant exposes the device configuration through generated entities.

The public defaults are anonymized. Runtime target routing is stored in device
text entities and can be populated by the Home Assistant blueprint from real
`media_player` and `light` entity selectors.

Version `1.2.0` improves touch target sizing, the light and weather layouts,
dynamic media status mirroring and the public guided installation path.

## License

MIT. See [LICENSE](LICENSE).
