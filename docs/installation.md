# Installation

This guide installs the Passion Wave Rotaryknob firmware in ESPHome and links it
to Home Assistant.

The intended public no-expert path is
`https://www.passion-wave.com/install/`. It currently delivers
V3.0.0-beta.2 as an explicitly marked prerelease; V2.1.1 remains the rollback
tag until physical acceptance is complete.

The customer still needs a USB data cable and a supported browser because Web
Serial talks directly to the selected ESP32 over USB. Use Chrome or Edge on desktop.
iOS browsers cannot do this flow.

## Planned Public Browser Install

This is the intended after-purchase flow:

1. Connect the Rotaryknob to the browser device with USB in the orientation
   that exposes the ESP32-S3.
2. Open `https://www.passion-wave.com/install/`.
3. Press `Install Rotaryknob`.
4. Let the installer perform a clean erase, verify the ESP32-S3 and flash
   `PassionWave Rotaryknob`.
5. At 100 percent keep the ESP Web Tools dialog open, press `Next`, provision
   Wi-Fi and verify the S3.
6. Unplug the cable, reverse the USB-C plug and reconnect it.
7. Let the installer perform a clean erase, verify the classic ESP32 and flash
   `PassionWave Rotaryknob Bridge`.
8. Keep the dialog open, press `Next`, provision Wi-Fi and verify both
   processors. If the browser does not reconnect Improv automatically, use the
   separate bridge Wi-Fi button; it reconnects without another flash.
9. Open Home Assistant and confirm both discovered ESPHome endpoints belonging
   to this one Rotaryknob. Home Assistant 2026.7 or newer automatically creates
   and provisions one unique API encryption key per endpoint; the customer is
   not asked to enter a key.

Wi-Fi credentials entered in this flow are sent over USB to the device. They are
not sent to Passion Wave.

The website repository contains the installer page and both factory manifests:

```text
https://www.passion-wave.com/firmware/rotaryknob/s3/manifest-3.0.0-beta.2.json
https://www.passion-wave.com/firmware/rotaryknob/esp32/manifest-3.0.0-beta.2.json
```

Both published binaries are built from sanitized public factory
configurations. Every new release must preserve these requirements:

- no private Wi-Fi credentials;
- no MQTT component or broker credentials;
- no private API encryption key;
- no private OTA password;
- `name_add_mac_suffix` enabled;
- `improv_serial` enabled for browser Wi-Fi setup;
- `captive_portal` enabled as fallback provisioning path;
- `dashboard_import` enabled for ESPHome adoption.
- automatic clean erase enabled in both Web Tools manifests through
  `new_install_prompt_erase: false`;
- no `home_assistant_domain` or Improv `next_url`; Home Assistant opens only in
  the final guided step;
- S3 deep sleep held back until the first Home Assistant API connection.

The installer must identify the chip before writing and refuse the wrong image.
The detailed target structure is documented in
[Customer product architecture](customer-product-architecture.md).

The current private development build must not be uploaded as the public
website firmware.

## Manual Maintainer / Developer Path

The manual steps below are only needed for maintainers and developers who build
or flash firmware themselves.

## 1. Prepare ESPHome

Install the ESPHome add-on in Home Assistant or use the ESPHome Docker image.
The dual-MCU candidate currently targets ESPHome `2026.7.0`.

Copy the repository `esphome/` folder into your ESPHome configuration
directory. Keep both role cores, the S3 UI core and the thin Managed
entrypoints:

- `esphome/rotaryknob-s3-ui-core.yaml`
- `esphome/dual-mcu-s3-core.yaml`
- `esphome/dual-mcu-esp32-core.yaml`
- `esphome/managed-production-s3.yaml`
- `esphome/managed-production-esp32.yaml`
- `esphome/scrollwheel_dynamic_targets.h`
- `esphome/squareline_font_bridge.h`
- `esphome/round_Temp/fonts/ui_font_Number.c`

## 2. Configure Secrets

Create or update `secrets.yaml` with:

```yaml
wifi_ssid: "your-wifi"
wifi_password: "your-password"
api_encryption_key: "replace-with-your-esphome-api-key"
ota_password: "replace-with-your-ota-password"
fallback_ap_password: "replace-with-your-fallback-ap-password"
ha_weather_entity: "weather.forecast_home"
weather_location_fallback: "Home"
home_assistant_base_url: "http://homeassistant.local:8123"
rain_radar_image_url: "http://homeassistant.local:8123/local/scrollwheel/rain_radar_z1.jpg"
photo_image_url_0: "http://homeassistant.local:8123/local/passion-wave/photo-0.jpg"
photo_image_url_1: "http://homeassistant.local:8123/local/passion-wave/photo-1.jpg"
photo_image_url_2: "http://homeassistant.local:8123/local/passion-wave/photo-2.jpg"
house_floorplan_image_url: "http://homeassistant.local:8123/local/passion-wave/floorplan-render/live.png"
```

Use a Home Assistant host name or IP address that the ESPHome device can
resolve. If `homeassistant.local` is unreliable on your network, use the fixed
Home Assistant IP address for `home_assistant_base_url` and the local image
URLs. `ha_weather_entity` must be an existing `weather.*` entity;
the firmware reads current temperature, location name and forecasts from that
entity.

## 3. Compile And Flash

From this repository:

```sh
./tools/config.sh esphome/managed-production-s3.yaml
./tools/config.sh esphome/managed-production-esp32.yaml
./tools/build.sh esphome/managed-production-s3.yaml
./tools/build.sh esphome/managed-production-esp32.yaml
```

If flashing at `460800` baud is unstable, use:

```sh
BAUD_RATE=115200 ./tools/flash.sh esphome/managed-production-s3.yaml
BAUD_RATE=115200 ./tools/flash.sh esphome/managed-production-esp32.yaml
```

After flashing, a device without access to the configured Wi-Fi network enters
offline promo demo mode automatically. This is useful for first product demos:
the UI shows local weather, light and media examples, but it does not call Home
Assistant or network image URLs. Once the configured Wi-Fi becomes
available, demo mode switches off by itself and the normal integration starts.
The persistent `scrollwheel Demo` switch, also reachable as `Demo` on the device
Settings page, enables or disables this offline promo behavior.

## 4. Select Targets In Home Assistant

After the device connects, open:

`Settings` -> `Devices & services` -> `ESPHome`. Add both `PassionWave
Rotaryknob` and `PassionWave Rotaryknob Bridge` as the two processor endpoints
of the same physical device.

The public factory image contains no pre-shared key. During the 20-minute
provisioning window, Home Assistant 2026.7 or newer creates a unique key for
each processor over the zero-PSK Noise provisioning connection. The resulting
Native API session is encrypted without exposing the key to the customer.
Authenticated OTA still requires the managed deployment step described in
[ESPHome API security lifecycle](api-security-lifecycle.md).

The simplest path is to import the device defaults blueprint first. It uses
Home Assistant entity pickers, so the user does not type entity IDs manually:

```text
home_assistant/blueprints/automation/passion_wave/rotaryknob_device_defaults.yaml
```

Create one automation from that blueprint and select:

- the ESPHome Rotaryknob S3/display device, not the ESP32 Bridge;
- one `media_player` entity. Home Assistant lists all media players. Choose a
  Music Assistant capable player if playlist, radio or podcast browsing should
  be available. For a Sonos speaker, choose its native Music Assistant entity
  rather than the generic Sonos integration entity. The latter supports basic
  transport and volume but does not own the Music Assistant queue.
- four `light` entities. Home Assistant lists all light entities.

The blueprint writes the selected entity IDs and friendly names into the
Rotaryknob text entities and reapplies them after Home Assistant starts or
automations are reloaded. It also relays media state, title, artist and cover
data whenever the selected media player changes. Those relay values drive the
Play/Pause icon, cover image and media cover screensaver for dynamically
selected media players.

Without this blueprint, the firmware still controls and tracks the media player
stored in `Rotaryknob Media Entity ID`. It polls Home Assistant through
`homeassistant.action` plus a `response_template`, so Play/Pause state, title,
artist, volume, progress and cover images work for dynamic media targets without
an extra automation. Use the blueprint when the customer should pick entities
from friendly Home Assistant selectors instead of typing entity IDs.

Manual fallback: these ESPHome entities can still be edited directly on the
device page if the blueprint is not used:

- `Rotaryknob Media Entity ID`
- `Rotaryknob Media Label`
- `Rotaryknob Light Slot 1 Entity ID`
- `Rotaryknob Light Slot 1 Label`
- `Rotaryknob Light Slot 2 Entity ID`
- `Rotaryknob Light Slot 2 Label`
- `Rotaryknob Light Slot 3 Entity ID`
- `Rotaryknob Light Slot 3 Label`
- `Rotaryknob Light Slot 4 Entity ID`
- `Rotaryknob Light Slot 4 Label`
- `scrollwheel Vibration`
- `scrollwheel Rotary Haptic Effect`
- `scrollwheel Timer Done Haptic Effect`
- `Screensaver Startverzögerung` (10–600 s, Standard 30 s)
- `Screensaver Abdunkeldauer` (100 % auf 10 %, 30–1800 s, Standard 300 s)
- `Wach halten` (Dev-Schalter, Standard aus)
- `Display Dimmverzögerung` (5–120 s, Standard 15 s)
- `Display Dimmhelligkeit` (5–30 %, Standard 10 %)
- `Display aus ohne Playback` (30–1800 s, Standard 60 s)
- `Display aus bei Playback` (60–3600 s, Standard 180 s)

The settings are stored persistently on the ESPHome device.

For an installed dual-MCU device, the same media target and all four light
entity IDs are declared once in `devices/production.yaml` or
`devices/test.yaml`. Both processor entrypoints include that overlay. A
differing target does not damage the device, but deliberately disables the
low-latency ESP32 bridge and reports
`HA-Bridge Zielkonfiguration abweichend`.

## 5. PassionWave Integration and Music Assistant

Copy `custom_components/passion_wave` into
`/config/custom_components/passion_wave`, restart Home Assistant and add
**PassionWave** under **Settings > Devices & services**.

Create one Config Entry per physical Rotaryknob. Select its Bridge entity
**PassionWave Integration Entry ID**, Music Assistant instance and Music
Assistant player. The integration synchronizes its stable Config Entry ID to
the Bridge and bounds every library/track page before it reaches firmware.
Playlist entries themselves are maintained in Music Assistant, not duplicated
in PassionWave. No blueprint, YAML media package, MQTT broker, token or copied
encryption key is required.

## 6. Rain Radar Package

Copy:

```text
home_assistant/packages/scrollwheel_rain_radar.yaml
```

to your Home Assistant `packages/` directory and enable packages in
`configuration.yaml` if needed:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

The package requires `ffmpeg` on the Home Assistant host. It creates the three
compact, baseline-compatible 320×320 JPEGs
`/local/scrollwheel/rain_radar_z0.jpg` through
`rain_radar_z2.jpg` using `yuvj420p`.

Install `home_assistant/pyscript/passion_wave_floorplan.py` in
`/config/pyscript/` and reload Pyscript. The script converts
`sensor.scrollwheel_rain_radar_image_path` into the absolute internal URL
`pyscript.passion_wave_radar_asset_url`. Current bridge firmware prefers this
native-API value and only uses `rain_radar_image_url` as its compile-time
fallback. The same script publishes the current floorplan URL in the
`asset_url` attribute of `pyscript.passion_wave_floorplan_revision`.

After updating this package, reload Home Assistant packages or restart Home
Assistant once so the lighter radar capture command is active.

See [Radar and floorplan data flow](radar-floorplan-data-flow.md) for the exact
runtime chain and its diagnostic checkpoints.

## 7. Optional Light mV Calibration Package

If a Zigbee rain/light sensor exposes brightness only as a raw millivolt-like
value, copy:

```text
home_assistant/packages/light_mv_calibration.yaml
```

to your Home Assistant `packages/` directory.

The package defaults to the detected raw sensor:

```text
sensor.outdoor_regenlichtsensor_illuminance_raw
```

It creates estimated lux, daylight class and calibration-helper entities. Open
`Settings` -> `Devices & services` -> `Helpers` and adjust the four anchor
values after observing the raw mV value in darkness, dim light, overcast
daylight and direct sun. See
[`docs/light-mv-calibration.md`](light-mv-calibration.md) for the model and the
limits of automatic recalibration.

## Known Limits

- Dynamic entity pickers live in Home Assistant through the blueprint. The
  ESPHome device page itself exposes persistent text fields because ESPHome text
  entities do not provide Home Assistant-wide dynamic dropdown options.
- ESPHome still cannot subscribe directly to arbitrary entity attributes from a
  runtime text field. Dynamic media state and cover reflection therefore uses a
  periodic `homeassistant.action` snapshot with `response_template`. The
  ESPHome integration must allow this device to perform Home Assistant actions.
- The weather source is still selected at compile time through
  `ha_weather_entity`. Set it to the desired `weather.*` entity before building.
- GitHub one-click dashboard import is prepared through `dashboard_import`, but
  ESPHome still needs the companion include files to be present. Until ESPHome
  supports bundling all include files through the dashboard import flow, the
  documented copy step remains the most reliable install path.
