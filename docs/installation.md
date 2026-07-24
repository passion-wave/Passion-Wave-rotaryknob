# Installation

This guide installs the Passion Wave Rotaryknob firmware in ESPHome and links it
to Home Assistant.

The intended public no-expert path is
`https://www.passion-wave.com/install/`. As of 2026-07-24 this path is a
prototype, not a retail-ready installer: the final device has two processors
and the current public manifest covers only one image.

The customer still needs a USB data cable and a supported browser because Web
Serial talks directly to the selected ESP32 over USB. Use Chrome or Edge on desktop.
iOS browsers cannot do this flow.

## Planned Public Browser Install

This is the intended after-purchase flow:

1. Connect the Rotaryknob to the browser device with USB in the orientation
   that exposes the ESP32-S3.
2. Open `https://www.passion-wave.com/install/`.
3. Press `Install Rotaryknob`.
4. Let the installer verify that the connected chip is the ESP32-S3 and flash
   the S3 factory image.
5. Provision Wi-Fi and verify the S3.
6. Unplug the cable, reverse the USB-C plug and reconnect it.
7. Let the installer verify that the connected chip is the classic ESP32 and
   flash the bridge factory image.
8. Provision Wi-Fi and verify both processors.
9. Open Home Assistant and complete the Passion Wave config flow.

Wi-Fi credentials entered in this flow are sent over USB to the device. They are
not sent to Passion Wave.

This browser path is technically possible and the website repository already
contains an installer page and a single firmware manifest. Before it can be
advertised for real customers, two factory manifests must be published:

```text
https://www.passion-wave.com/firmware/rotaryknob/s3/manifest.json
https://www.passion-wave.com/firmware/rotaryknob/esp32/manifest.json
```

Both binaries must be built from sanitized public factory configurations:

- no private Wi-Fi credentials;
- no private MQTT credentials;
- no private API encryption key;
- no private OTA password;
- `name_add_mac_suffix` enabled;
- `improv_serial` enabled for browser Wi-Fi setup;
- `captive_portal` enabled as fallback provisioning path;
- `dashboard_import` enabled for ESPHome adoption.

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
directory, so the YAML is available as `esphome/passion-wave-rotaryknob.yaml`.
Keep this structure:

- `esphome/passion-wave-rotaryknob.yaml`
- `esphome/scrollwheel_dynamic_targets.h`
- `esphome/squareline_font_bridge.h`
- `esphome/round_Temp/fonts/ui_font_Number.c`

## 2. Configure Secrets

Create or update `secrets.yaml` with:

```yaml
wifi_ssid: "your-wifi"
wifi_password: "your-password"
mqtt_host: "homeassistant.local"
mqtt_username: "your-mqtt-user"
mqtt_password: "your-mqtt-password"
api_encryption_key: "replace-with-your-esphome-api-key"
ota_password: "replace-with-your-ota-password"
fallback_ap_password: "replace-with-your-fallback-ap-password"
ha_weather_entity: "weather.forecast_home"
weather_location_fallback: "Home"
home_assistant_base_url: "http://homeassistant.local:8123"
rain_radar_image_url: "http://homeassistant.local:8123/local/scrollwheel/rain_radar.jpg"
photo_image_url_0: "http://homeassistant.local:8123/local/passion-wave/photo-0.jpg"
photo_image_url_1: "http://homeassistant.local:8123/local/passion-wave/photo-1.jpg"
photo_image_url_2: "http://homeassistant.local:8123/local/passion-wave/photo-2.jpg"
house_floorplan_image_url: "http://homeassistant.local:8123/local/passion-wave/floorplan.png"
```

Use a Home Assistant host name or IP address that the ESPHome device can
resolve. If `homeassistant.local` is unreliable on your network, use the fixed
Home Assistant IP address for `mqtt_host`, `home_assistant_base_url` and the
local image URLs. `ha_weather_entity` must be an existing `weather.*` entity;
the firmware reads current temperature, location name and forecasts from that
entity.

## 3. Compile And Flash

From this repository:

```sh
./tools/config.sh esphome/passion-wave-rotaryknob.yaml
./tools/build.sh esphome/passion-wave-rotaryknob.yaml
./tools/flash.sh esphome/passion-wave-rotaryknob.yaml
```

If flashing at `460800` baud is unstable, use:

```sh
BAUD_RATE=115200 ./tools/flash.sh esphome/passion-wave-rotaryknob.yaml
```

After flashing, a device without access to the configured Wi-Fi network enters
offline promo demo mode automatically. This is useful for first product demos:
the UI shows local weather, light and media examples, but it does not call Home
Assistant, MQTT or network image URLs. Once the configured Wi-Fi becomes
available, demo mode switches off by itself and the normal integration starts.
The persistent `scrollwheel Demo` switch, also reachable as `Demo` on the device
Settings page, enables or disables this offline promo behavior.

## 4. Select Targets In Home Assistant

After the device connects, open:

`Settings` -> `Devices & services` -> `ESPHome` -> `Passion Wave Rotaryknob`.

The simplest path is to import the device defaults blueprint first. It uses
Home Assistant entity pickers, so the user does not type entity IDs manually:

```text
home_assistant/blueprints/automation/passion_wave/rotaryknob_device_defaults.yaml
```

Create one automation from that blueprint and select:

- the ESPHome Rotaryknob device;
- one `media_player` entity. Home Assistant lists all media players. Choose a
  Music Assistant capable player if playlist, radio or podcast browsing should
  be available.
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
- `scrollwheel Screensaver Timeout`

The settings are stored persistently on the ESPHome device.

## 5. Optional Music Assistant Library Blueprint

For the Music Assistant media library, also import:

```text
home_assistant/blueprints/automation/passion_wave/rotaryknob_music_assistant_library.yaml
```

Create an automation from that blueprint and select your Music Assistant config
entry. It publishes compact retained playlist, radio and podcast bootstrap
lists and answers the device's paged playlist and playlist-track requests.

The media target selection is separate from the media library list. Playlist,
radio and podcast entries are loaded from MQTT topics:

- `passion_wave/media/playlists`
- `passion_wave/media/radios`
- `passion_wave/media/podcasts`
- paged playlist responses on `passion_wave/media/playlists/state`
- playlist-track responses on `passion_wave/media/playlist_tracks/state`

Populate these topics from Music Assistant with retained JSON payloads, or run a
Home Assistant automation that listens for
`passion_wave/media/playlists/request` and
`passion_wave/media/playlist_tracks/request`. Without that bridge the media
player can still be controlled, but the selection list is empty.

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

The package requires `ffmpeg` on the Home Assistant host.
It creates `/local/scrollwheel/rain_radar.jpg` as a compact `320 x 320`
baseline-compatible JPEG using `yuvj420p`; use that path for
`rain_radar_image_url`. If
`sensor.scrollwheel_rain_radar_image_path` exists, the firmware prefers that
dynamic Home Assistant path and only falls back to the compile-time URL.

After updating this package, reload Home Assistant packages or restart Home
Assistant once so the lighter radar capture command is active.

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
