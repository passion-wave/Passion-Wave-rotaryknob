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

## Repository Layout

- `esphome/`: ESPHome firmware and required local include files.
- `home_assistant/blueprints/`: optional Home Assistant automation blueprint.
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
4. In Home Assistant, open the ESPHome device page and configure the Text
   entities for media and light routing, or use the optional blueprint with
   Home Assistant entity pickers.
5. Optionally import the Home Assistant blueprint from
   `home_assistant/blueprints/automation/passion_wave/rotaryknob_device_defaults.yaml`
   to apply a repeatable default wiring after Home Assistant restarts.

See [docs/installation.md](docs/installation.md) for the complete setup.

## Current Blueprint Scope

This repository provides an ESPHome firmware blueprint and an optional Home
Assistant automation blueprint. ESPHome owns the runtime UI and service calls;
Home Assistant exposes the device configuration through generated entities.

The public defaults are anonymized. Runtime target routing is stored in device
text entities and can be populated by the Home Assistant blueprint from real
`media_player` and `light` entity selectors.

## License

MIT. See [LICENSE](LICENSE).
