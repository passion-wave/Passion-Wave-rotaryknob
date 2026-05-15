# Installation

This guide installs the Passion Wave Rotaryknob firmware in ESPHome and links it
to Home Assistant.

## 1. Prepare ESPHome

Install the ESPHome add-on in Home Assistant or use the ESPHome Docker image.
The firmware currently targets ESPHome `2026.2.2`.

Copy the repository `esphome/` folder into your ESPHome configuration
directory, so the YAML is available as `esphome/passion-wave-rotaryknob.yaml`.
Keep this structure:

- `esphome/passion-wave-rotaryknob.yaml`
- `esphome/scrollwheel_dynamic_targets.h`
- `esphome/encoder_pulse_decoder.h`
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
home_assistant_base_url: "http://homeassistant.local:8123"
rain_radar_image_url: "http://homeassistant.local:8123/local/passion-wave/rain_radar.jpg"
photo_image_url_0: "http://homeassistant.local:8123/local/passion-wave/photo-0.jpg"
photo_image_url_1: "http://homeassistant.local:8123/local/passion-wave/photo-1.jpg"
photo_image_url_2: "http://homeassistant.local:8123/local/passion-wave/photo-2.jpg"
house_floorplan_image_url: "http://homeassistant.local:8123/local/passion-wave/floorplan.png"
```

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

## 4. Configure In Home Assistant

After the device connects, open:

`Settings` -> `Devices & services` -> `ESPHome` -> `Passion Wave Rotaryknob`.

Configure these entities:

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

## 5. Optional Home Assistant Blueprint

Import:

```text
home_assistant/blueprints/automation/passion_wave/rotaryknob_device_defaults.yaml
```

Create an automation from the blueprint, select the ESPHome device and choose:

- a `media_player` entity for media playback. For playlist, radio and podcast
  use, choose a player that is controllable by Music Assistant.
- four `light` entities for the light slots.

The blueprint writes the selected entity IDs and friendly names into the
Rotaryknob text entities and reapplies them after Home Assistant starts or
automations are reloaded.

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

## Known Limits

- The dynamic entity picker lives in Home Assistant through the optional
  blueprint. The ESPHome device page itself exposes persistent text fields,
  because ESPHome text entities do not provide Home Assistant-wide dynamic
  dropdown options.
- The firmware sends service calls to the configured entity IDs. Some status
  sensors still use the compile-time fallback entities for initial display state,
  so freshly selected entities may show local optimistic state until Home
  Assistant service calls update them.
- GitHub one-click dashboard import is prepared through `dashboard_import`, but
  ESPHome still needs the companion include files to be present. Until ESPHome
  supports bundling all include files through the dashboard import flow, the
  documented copy step remains the most reliable install path.
