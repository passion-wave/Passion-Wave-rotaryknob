# Dual-MCU compatibility test

Current test versions: S3 `1.2.0-ui-next.98`, ESP32
`1.2.0-ha-bridge.50`.

This test runs both processors of a dedicated second physical Rotaryknob and
keeps every runtime feature from firmware 1.2.0 available. The first physical
device, currently named `passion_wave_rotaryknob` in Home Assistant, remains
online on firmware 1.2.0 and is not modified. The feature migration has reached
the intended processor boundary; the test remains a qualification candidate,
not a retail factory release.

## What runs where

| Physical device / processor | ESPHome configuration | Responsibilities | Home Assistant device |
| --- | --- | --- | --- |
| Production device | none; remains untouched | Existing complete firmware 1.2.0 | Existing `passion_wave_rotaryknob` |
| Test device / ESP32-S3 | `dual-mcu-test-s3.yaml` | Complete 1.2.0 application plus authoritative EC1 hardware-PCNT reader | New Passion Wave Rotaryknob Test S3 |
| Test device / ESP32-U4WDH | `dual-mcu-test-esp32.yaml` | EC2 diagnostics, Home Assistant bridge, forecast/radar and retained Music Assistant list parsing | New Passion Wave Rotaryknob Test ESP32 |

The S3 configuration includes `passion-wave-rotaryknob.yaml` as a local
ESPHome package. ESPHome merges the diagnostic additions by component ID, so
the original 1.2.0 implementation is not duplicated or selectively rewritten.
EC1 remains authoritative during this test. Two S3 hardware-PCNT units retain
fast pulses independently of the application loop. EC2 is measured in parallel
but never applied to UI state; otherwise every physical detent would be counted
twice.

Neither test configuration enables Bluetooth, BLE tracking, a Bluetooth proxy
or Improv provisioning. Wi-Fi credentials come from `secrets.yaml`.

The test nodes use the unique hostnames
`passion-wave-rotary-test-s3` and
`passion-wave-rotary-test-esp32`. They must never be changed to
`passion-wave-rotaryknob` while the production device is online. The shared
Music Assistant request/state topics can serve both physical devices because
their request IDs include the unique ESPHome node name. The test S3 uses a
separate media-debug topic so diagnostic messages cannot be confused with the
production device.

## Files required by ESPHome Device Builder

Copy the complete repository `esphome/` directory into Home Assistant's
`/config/esphome/` directory, but omit the local `.esphome/` build-cache
directory. In particular, the test needs:

- `dual-mcu-test-s3.yaml`
- `dual-mcu-test-esp32.yaml`
- `dual_mcu_link.h`
- `dual_mcu_encoder.h`
- `dual_mcu_radar_proxy.h`
- `dual_mcu_library_proxy.h`
- `ec1_pcnt_encoder.h`
- `passion-wave-rotaryknob.yaml`
- `scrollwheel_dynamic_targets.h`
- `squareline_font_bridge.h`
- `round_Temp/fonts/ui_font_Number.c`
- `secrets.yaml`

The existing 1.2.0 secrets remain required because the S3 still provides the
complete application. Use `secrets.example.yaml` as the key list, but never
copy real credentials into version control.

## Home Assistant and ESPHome setup

It is not necessary to create an ESPHome integration device in Home Assistant
before flashing. The two concepts are separate:

1. **ESPHome Device Builder App:** stores YAML, validates, compiles and flashes
   firmware. Placing the YAML files in `/config/esphome/` creates the two
   build configurations in its dashboard; a separate project wizard is not
   required.
2. **ESPHome integration:** connects a running device to Home Assistant through
   the native API. Home Assistant normally discovers it after the first
   successful Wi-Fi boot.

If the ESPHome Device Builder dashboard does not refresh after copying the
files, restart only the ESPHome Device Builder App or use **Import from File**
for the two test YAML files. Do not replace `secrets.yaml` when it already
contains the working configuration. Do not select, adopt, migrate, overwrite,
rename or install anything on the online production node
`passion-wave-rotaryknob`.

## Flash sequence

The board routes the USB connector to a different processor depending on plug
orientation. Always identify the connected chip before installing firmware.

1. Disconnect the board from USB.
2. Connect the orientation that exposes the **ESP32-S3**. Verify that the serial
   device/chip identification reports ESP32-S3; it commonly appears as
   `/dev/cu.usbmodem...` on macOS.
3. In ESPHome Device Builder, open `dual-mcu-test-s3.yaml`, select **Validate**,
   then **Install** and flash this configuration to the S3.
4. Disconnect USB. Rotate the USB-C plug at the device by 180 degrees and
   reconnect it.
5. Verify that this orientation exposes the classic **ESP32 / ESP32-U4WDH**;
   it commonly appears as `/dev/cu.usbserial...` on macOS.
6. Open `dual-mcu-test-esp32.yaml`, select **Validate**, then **Install** and
   flash this configuration to the ESP32.
7. Power-cycle the complete board after both installations.

Never flash the 16 MB S3 image to the 4 MB ESP32 or the ESP32 coprocessor image
to the S3. If chip identification is ambiguous, stop before pressing Install.

The two test processors use their own node names and can subsequently receive
OTA updates independently. The production device keeps its existing node name,
integration entry, entities and firmware without any interruption.

## Add both devices to Home Assistant

After both processors of the test object join Wi-Fi, Home Assistant should
contain three ESPHome devices in total: one production device and two devices
belonging to the test object.

1. Open **Settings > Devices & services**.
2. Confirm that the existing production device `passion_wave_rotaryknob`
   remains available. Do not choose Migrate or Overwrite for this entry.
3. Under **Discovered**, configure **Passion Wave Rotaryknob Test S3**.
4. Configure **Passion Wave Rotaryknob Test ESP32** as a second new entry.
5. If discovery fails, add the ESPHome integration manually for each hostname:
   - `passion-wave-rotary-test-s3.local`, port `6053`;
   - `passion-wave-rotary-test-esp32.local`, port `6053`.
6. When requested, use the native API encryption key from `secrets.yaml`.
7. Open the ESPHome integration options for **both test processors** and enable
   **Allow the device to perform Home Assistant actions**. The S3 uses this
   only when `S3 Network Rescue Mode` is deliberately enabled; the ESP32 needs
   it for migrated controls and `weather.get_forecasts`. Do not change this
   option on the production device merely for the test.
8. Create a second automation from the existing **Passion Wave Rotaryknob -
   Dynamic Targets** blueprint. Select only **Passion Wave Rotaryknob Test S3**
   and assign its media player and four light slots. Leave the production
   automation unchanged.

The Music Assistant Library Bridge listens on shared, request-ID-scoped MQTT
topics, so one existing bridge automation can serve both physical devices. Do
not create a duplicate Music Assistant bridge unless a separate MQTT namespace
is deliberately configured later.

Both processors intentionally use the native ESPHome API in this compatibility
test. The final performance architecture will remove normal S3 network traffic
only after all 1.2.0 network responsibilities have been migrated and tested on
the ESP32.

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
- Opening Radar ends with `S3 Radar Proxy Status` = `Bild aktiv`, a positive
  byte count and `ESP32 Radar Proxy Status` = `Bereit` while both UART error
  counters remain unchanged.
- `S3 Library Proxy Status` reports received ESP32 lists; playlists, radios
  and podcasts remain selectable. If the ESP32 link is interrupted, the S3
  reports the bridge error without automatically starting MQTT. Only the
  explicit Rescue switch may start the compatibility path.
- The Ping buttons produce a finite link latency.
- Disconnecting or resetting the coprocessor does not stop EC1 from controlling
  the S3 interface.
- The production device remains available and its existing entity states do
  not become unavailable during installation or testing.

Then regress every 1.2.0 function: touch navigation, haptics, all light and
scene controls, media playback and volume, Music Assistant MQTT lists, weather,
rain radar, photos/floorplan, timer, alarm, screensavers, display sleep and the
offline demo. EC2 must not become authoritative unless a later hardware and
firmware investigation first demonstrates reliable unit-step behavior.

# OTA and rescue operation

Both processors are independent ESPHome OTA targets:

- ESP32-S3 display processor: `passion-wave-rotary-test-s3`
- classic ESP32 network processor: `passion-wave-rotary-test-esp32`

Always compile both profiles before installing a migration revision. Upload
only to the matching target; the S3 image is not compatible with the classic
ESP32 and vice versa. A normal migration must leave Wi-Fi, encrypted native
API, ESPHome OTA and Safe Mode enabled on both processors.

From S3 revision `.88`, a missing ESP32 bridge does not automatically start
the compatibility MQTT path. If deliberate recovery is required, enable
`S3 Network Rescue Mode` on the S3 device in Home Assistant. Rescue starts S3
MQTT and refreshes the compatibility weather/library path. Disable it again
after diagnosis. The switch always returns to off after an S3 reboot.

From revision `.89`, the same Rescue gate protects every direct S3 asset
download. Radar, photos, floorplan and media covers normally arrive only over
the ESP32 UART asset stream. A missing bridge shows an unavailable/waiting
state instead of silently activating S3 HTTP.
