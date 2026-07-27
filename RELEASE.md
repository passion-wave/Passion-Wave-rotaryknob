# Version 3.0.0-beta.2

Release description: `native-integration,bridge-owned-network`

## Status

Public prerelease candidate for tag `v3.0.0-beta.2`. Both chip images compile
from this source and are distributed together. Physical clean-device
acceptance remains deliberately pending and is the gate for promotion beyond
beta, not for publishing this explicitly marked prerelease.

Beta.2 supersedes beta.0 and beta.1 before any customer flash. Beta.0 reused
stable firmware URLs; beta.1 added query keys, but the production CDN did not
reliably include those keys in its cache identity. Beta.2 gives every manifest
and Factory image a unique version-bearing filename. The installer therefore
cannot resolve either processor to an artifact from an older release.

## Breaking architecture changes

- The standalone Single-MCU build entrypoint has been removed.
- MQTT, the Music Assistant setup blueprint and the YAML playlist helper are
  not part of V3.
- Home Assistant configuration is owned by the `passion_wave` Custom
  Integration and its typed Config Flow.
- The Bridge stores one PassionWave Config Entry ID and calls the bounded
  `passion_wave.get_library` and `passion_wave.get_playlist_tracks` services.
- Playlist, radio and podcast entries are the current Music Assistant library;
  PassionWave keeps no separately editable copy.
- The Config/Options Flow can optionally restrict each media category through
  searchable multi-select fields. Existing entries default to the complete
  library, and only stable Music Assistant URIs are stored.
- The S3 has no application-network rescue path, HA application-state
  subscriptions or SNTP client. Its runtime network surface is provisioning,
  encrypted ESPHome Native API and OTA.
- Application state, commands, media pages and image assets cross the 2 Mbit/s
  framed UART link through the classic ESP32 Bridge.

## Responsiveness contract

- The S3 remains the owner of touch, EC1, LVGL, haptics and optimistic drawing.
- Home Assistant and Music Assistant work never blocks local input rendering.
- Library and playlist-track responses are bounded before they reach firmware.
- The next page is requested with five visible rows remaining and duplicate
  in-flight requests are suppressed.

## Coordinated upgrade order

1. Install `custom_components/passion_wave` and restart Home Assistant.
2. Add one PassionWave Config Entry per physical Rotaryknob.
3. Build both MCU images from this exact source version.
4. Update the Bridge and verify its encrypted Native API connection.
5. Update the matching S3.
6. Verify playlist/radio/podcast bootstrap, five-row prefetch, track paging,
   playback, radar, floorplan, covers, lights, weather and display idle logic.

Never leave the two chips of one physical device on mixed V2/V3 firmware.
Rollback also requires rolling back both processors together.

## Source structure

- `custom_components/passion_wave/`: Home Assistant integration.
- `esphome/rotaryknob-s3-ui-core.yaml`: S3-local UI and hardware code.
- `esphome/dual-mcu-s3-core.yaml`: UART-backed S3 role.
- `esphome/dual-mcu-esp32-core.yaml`: Home Assistant Bridge role.
- `esphome/managed-*.yaml`: private OTA entrypoints.
- `esphome/factory-*.yaml`: credential-free onboarding entrypoints.
- `docs/native-api-migration.md`: migration and acceptance details.

## Verified candidate

- ESPHome `2026.7.0` configuration validation: Managed and Factory S3/Bridge
  entrypoints valid.
- Factory Bridge build: 41.0% RAM, 61.6% Flash.
- Factory S3 build: 54.1% internal RAM, 71.5% Flash.
- Resolved S3 profile: no MQTT or SNTP platform and no direct image-download
  call in the S3 UI source.
- PassionWave response normalization: four unit tests passed; Python and JSON
  files compile/parse successfully.
- `media_player.browse_media` request and response contract checked against
  Home Assistant `2026.7.4`.

Verified public Factory artifacts:

```text
f23db0fcefa9a56512bf7d16195a91671ab323f58d66df42e707e7acb070f45f  s3/passion-wave-rotaryknob-s3-3.0.0-beta.2.factory.bin
cee877c04eaa9caf7df07f192505f8557e43d4bbb56ff5995179c98196563fe0  esp32/passion-wave-rotaryknob-esp32-3.0.0-beta.2.factory.bin
```

The ESPHome/LVGL build still reports upstream deprecation warnings for the
legacy `online_image` declaration form, QSPI DBI and ArduinoJson compatibility
types. They do not fail this beta build; migration to the new ESPHome image
platform remains follow-up work before its announced removal window.
