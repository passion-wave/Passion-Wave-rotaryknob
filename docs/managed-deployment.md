# Dual-MCU managed deployment

> V3 is intentionally MQTT-free and not backward compatible.

The coordinated version is defined only in [`../VERSION`](../VERSION).

Deployment status for the current integration, both ECU firmwares and public artifacts
are qualified by `tools/qualify-release.sh`. Installation is delivered through
the single logical PassionWave firmware entity in Home Assistant, which updates
Bridge first and S3 second. See `release-runbook.md` for the complete release,
HACS and live-device rollout gates. Physical display acceptance and the
long-duration power measurement remain explicitly separate from automated
evidence.

One physical RotaryKnob contains two separately addressable ESPHome endpoints:
S3/display and ESP32/bridge. The repository contains entrypoints for two
physical RotaryKnobs and therefore four endpoints. Source configuration alone
confirms neither physical pair. The dated rollout recorded in
[RELEASE.md](../RELEASE.md) updated Timo and
then Marco through their logical Home Assistant entities. Both physical pairs
ended with Bridge and S3 on the coordinated version, both connections active and no update
error. Configured entrypoints must never be mistaken for future live evidence.
Every device uses the same release sources and Managed security policy. Only
stable network identity, build directory and physical-device target overlay
differ. This avoids copied configurations while preserving independent OTA
recovery for each processor.

## What runs where

| Physical device / processor | ESPHome configuration | Responsibilities | Home Assistant device |
| --- | --- | --- | --- |
| Production / ESP32-S3 | `managed-production-s3.yaml` | Display, EC1, touch, LVGL, haptics and local UI | PassionWave RotaryKnob |
| Production / ESP32-U4WDH | `managed-production-esp32.yaml` | Home Assistant bridge, weather, network assets and library paging | PassionWave RotaryKnob Bridge |
| Device 2 / ESP32-S3 | `managed-test-s3.yaml` | Same S3 release with second identity and targets | PassionWave RotaryKnob 2 |
| Device 2 / ESP32-U4WDH | `managed-test-esp32.yaml` | Same bridge release with second identity and targets | PassionWave RotaryKnob Bridge 2 |

For the current installation the stable OTA targets are:

| Endpoint | Hostname | LAN address |
| --- | --- | --- |
| Device 1 S3 | `passion-wave-managed-1-s3.local` | installation-specific |
| Device 1 bridge | `passion-wave-managed-1-bridge.local` | installation-specific |
| Device 2 S3 | `passion-wave-managed-2-s3.local` | installation-specific |
| Device 2 bridge | `passion-wave-managed-2-bridge.local` | installation-specific |

`managed-s3.yaml` and `managed-esp32.yaml` compose the role-specific cores with
`managed-common.yaml`. The four entrypoints add exactly one device overlay from
`devices/`. EC1 remains authoritative; EC2 is diagnostic comparison data and
is never applied to UI state.

Managed configurations do not enable Bluetooth, BLE tracking, a Bluetooth
proxy or Improv provisioning. Wi-Fi credentials come from `secrets.yaml`.

All endpoint hostnames remain unique. Music Assistant request IDs are derived
from the active ESPHome node name, so multiple physical devices can safely use
the shared service path without collisions.

## Files required by ESPHome Device Builder

Copy the complete repository `esphome/` directory into Home Assistant's
`/config/esphome/` directory, but omit the local `.esphome/` build-cache
directory. In particular, the test needs:

- `managed-common.yaml`
- `managed-s3.yaml`
- `managed-esp32.yaml`
- `managed-production-s3.yaml`
- `managed-production-esp32.yaml`
- `managed-test-s3.yaml`
- `managed-test-esp32.yaml`
- `devices/production.yaml`
- `devices/test.yaml`
- `dual_mcu_link.h`
- `dual_mcu_encoder.h`
- `dual_mcu_radar_proxy.h`
- `dual_mcu_library_proxy.h`
- `ec1_pcnt_encoder.h`
- `rotaryknob-s3-ui-core.yaml`
- `scrollwheel_dynamic_targets.h`
- `squareline_font_bridge.h`
- `round_Temp/fonts/ui_font_Number.c`
- `secrets.yaml`

Use `secrets.example.yaml` as the private transport-key list, but never copy
real credentials into version control.

## Home Assistant and ESPHome setup

It is not necessary to create an ESPHome integration device in Home Assistant
before flashing. The two concepts are separate:

1. **ESPHome Device Builder App:** stores YAML, validates, compiles and flashes
   firmware. Placing the YAML files in `/config/esphome/` creates four thin
   build configurations for the two configured device identities; a
   separate project wizard is not required.
2. **ESPHome integration:** connects a running device to Home Assistant through
   the native API. Home Assistant normally discovers it after the first
   successful Wi-Fi boot.

If the ESPHome Device Builder dashboard does not refresh after copying the
files, restart only the ESPHome Device Builder App or use **Import from File**
for the four Managed entrypoints. Do not replace `secrets.yaml` when it already
contains the working configuration.

## Flash sequence

The board routes the USB connector to a different processor depending on plug
orientation. Always identify the connected chip before installing firmware.

1. Disconnect the board from USB.
2. Connect the orientation that exposes the **ESP32-S3**. Verify that the serial
   device/chip identification reports ESP32-S3; it commonly appears as
   `/dev/cu.usbmodem...` on macOS.
3. In ESPHome Device Builder, open the matching
   `managed-{production,test}-s3.yaml`, select **Validate**, then **Install**
   and flash this configuration to the S3.
4. Disconnect USB. Rotate the USB-C plug at the device by 180 degrees and
   reconnect it.
5. Verify that this orientation exposes the classic **ESP32 / ESP32-U4WDH**;
   it commonly appears as `/dev/cu.usbserial...` on macOS.
6. Open the matching `managed-{production,test}-esp32.yaml`, select
   **Validate**, then **Install** and flash this configuration to the ESP32.
7. Power-cycle the complete board after both installations.

The classic ESP32 owns radar, photo, cover and floorplan downloads. Therefore
its private wrapper must contain the same `home_assistant_base_url`, photo and
`house_floorplan_image_url` substitutions as the S3 wrapper. Prefer the numeric
Home Assistant LAN address here; `.local` is resolved explicitly but depends
on Home Assistant advertising the expected mDNS hostname. The generated ESP32
configuration must point to `floorplan-render/live.png` when the dynamic
floorplan renderer is used.

Never flash the 16 MB S3 image to the 4 MB ESP32 or the ESP32 coprocessor image
to the S3. If chip identification is ambiguous, stop before pressing Install.

Every processor endpoint retains its existing node name and can subsequently
receive OTA updates independently.

For the known local installation, maintainers can update the four endpoints in
the documented order with:

```bash
export PW_DEVICE_1_S3_HOST="<device-1-s3-host-or-ip>"
export PW_DEVICE_1_BRIDGE_HOST="<device-1-bridge-host-or-ip>"
export PW_DEVICE_2_S3_HOST="<device-2-s3-host-or-ip>"
export PW_DEVICE_2_BRIDGE_HOST="<device-2-bridge-host-or-ip>"
./tools/upload-managed-pair.sh --devices-awake
```

The explicit flag is a safety interlock: both physical devices must be awake
before the command starts. The script requires four explicit targets and never
discovers or flashes an ambiguous endpoint.

## Register the devices in Home Assistant

After both processors join Wi-Fi, Home Assistant should contain two technical
ESPHome endpoints for each physical RotaryKnob. With both configured devices
online that means four endpoints in total, but still only two product devices.

1. Open **Settings > Devices & services**.
2. Confirm that both production endpoints remain available.
3. Confirm **PassionWave RotaryKnob 2**.
4. Confirm **PassionWave RotaryKnob Bridge 2**.
5. If discovery fails, add the ESPHome integration manually for the missing hostname:
   - `passion-wave-managed-2-s3.local`, port `6053`;
   - `passion-wave-managed-2-bridge.local`, port `6053`.
6. When requested during the controlled Factory-to-Managed migration, use the
   Native API encryption key from private `secrets.yaml`.
7. Leave **Allow the device to perform Home Assistant actions** disabled on
   both endpoints. The PassionWave integration validates bounded command
   states and answers through named ESPHome API actions; neither processor
   requires broad Home Assistant action permission.
8. Add one PassionWave Config Entry per physical RotaryKnob and bind it to that
   device's Display/S3, Bridge registration entity, Music Assistant instance,
   player and four ordered light positions.
9. Reopen **Configure** on the PassionWave entry for every later target change;
   no blueprint or manual ESPHome text edit is part of the customer path.

Each physical RotaryKnob and PassionWave Config Entry is isolated by its stable
entry ID. There are no shared MQTT topics or Music Assistant setup automations,
so additional devices do not change the configuration contract.

Both processors intentionally retain the native ESPHome API for management.
In Version 3, normal application data is owned by the bridge; the S3 network is
limited to provisioning, native API and OTA.

## Acceptance test

First reset the diagnostic counters, then turn the knob slowly through at least
20 detents in each direction, followed by several fast full spins.

- `S3 Link Connected` and `ESP32 Coprocessor Link` remain on.
- `EC1 Encoder Ready` is on; `EC1 Encoder Read Errors` remains zero.
- EC1 changes by exactly one for each slow detent and retains the expected
  movement during fast spins.
- EC2 is comparison data only. Its observed large jumps may produce a growing
  EC1/EC2 difference and must not be interpreted as an EC1 UI error.
- `UART Protocol Errors` and `Inter-MCU Protocol Errors` remain zero.
- `Coprocessor Status` reports `ESP32 HA-Bridge + Forecast aktiv`; the weather
  context shows tomorrow and the following day as daily Min/Max summaries.
- `ESP32 Daily Forecast Conditions` and `S3 Forecast Conditions Received`
  contain the same raw condition sequence. Equal icons are correct when these
  raw values are equal.
- Opening Radar ends with `S3 Radar Proxy Status` = `Asset aktiv: radar`, a positive
  byte count and `ESP32 Radar Proxy Status` = `Bereit` while both UART error
  counters remain unchanged.
- Opening House ends with `S3 Radar Proxy Status` = `Asset aktiv: house`, a
  positive byte count and the live floorplan instead of `Hausbild fehlt`.
  The same path can be tested without touch through the S3 API action
  `house_refresh`.
- `S3 Library Proxy Status` reports received ESP32 lists; playlists, radios
  and podcasts remain selectable. If the ESP32 link is interrupted, the S3
  reports the bridge error without starting MQTT or a compatibility network
  path.
- The Ping buttons produce a finite link latency.
- Disconnecting or resetting the coprocessor does not stop EC1 from controlling
  the S3 interface.
- The production device remains available and its existing entity states do
  not become unavailable during installation or testing.

Then regress every V3 function: touch navigation, haptics, all light and
scene controls, media playback and volume, Music Assistant API lists, weather,
rain radar, photos/floorplan, timer, alarm, screensavers, display sleep and the
offline demo. EC2 must not become authoritative unless a later hardware and
firmware investigation first demonstrates reliable unit-step behavior.

# OTA and recovery operation

Both processors are independent ESPHome OTA targets:

- Device 1 ESP32-S3: `passion-wave-managed-1-s3`
- Device 1 classic ESP32: `passion-wave-managed-1-bridge`
- Device 2 ESP32-S3: `passion-wave-managed-2-s3`
- Device 2 classic ESP32: `passion-wave-managed-2-bridge`

Always compile both profiles before installing a migration revision. Upload
only to the matching target; the S3 image is not compatible with the classic
ESP32 and vice versa. A normal migration must leave Wi-Fi, encrypted native
API, ESPHome OTA and Safe Mode enabled on both processors.

V3 has no S3 application-network rescue mode. A missing Bridge leaves remote
features unavailable while the local UI, timer, alarm and EC1 remain
responsive. Recover through the independent Bridge serial/OTA path, then
restart the pair. Radar, photos, floorplan and media covers always arrive over
the ESP32 UART asset stream.
