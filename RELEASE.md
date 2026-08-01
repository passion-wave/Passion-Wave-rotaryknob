# Version 3.0.0-beta.12

Release description: `customer-update-reconnect-hardening`

## Status

Public prerelease for firmware and Home Assistant integration. Both processor
images are built from this source and must always be installed as one
coordinated release.

## Customer-visible changes

- Home Assistant discovers one PassionWave Rotaryknob per physical product
  instead of exposing two ESPHome setup tiles.
- One PassionWave firmware update installs Bridge first, verifies its reconnect
  and then installs and verifies the S3 display processor.
- The two native ESPHome update entities remain available as hidden recovery
  transports.
- Configuration of Music Assistant, player, ordered light slots and media
  visibility is owned by the PassionWave Config Entry.
- Playlist and track paging continue when Music Assistant omits a total count.
- Media title glyphs, external light-state updates, Hue/WLED detail scenes,
  screensaver timing and volume feedback are consolidated in this beta.
- Home Assistant commands use the bounded PassionWave broker; ESPHome's broad
  Home Assistant action permission remains disabled.
- Album covers now load through the selected Home Assistant media player and
  can replace the active weather screensaver after the playback delay.
- The S3 cover pipeline keeps a safe memory reserve without blocking normal
  operation once the compiled weather photographs are resident.
- Media presentation is reconciled after reconnects, and Bridge discovery is
  kept behind the single PassionWave product flow.
- Firmware update manifests use the published PassionWave site directly.
- The coordinated updater refreshes ESPHome's Bridge action registration before
  starting the S3 phase, including when an OTA changes the compiled node name.
- A forecast request missed during reconnect is retried every ten seconds until
  the first valid daily response reaches the Bridge.

## Coordinated customer update

1. Update the PassionWave integration through HACS and restart Home Assistant.
2. Open the single `PassionWave Rotaryknob Firmware` update entity.
3. Press **Install** once.
4. Wait for Bridge update and verified reconnect.
5. Wait for S3 update and verified reconnect.

The sequence stops before touching the S3 if the Bridge cannot be verified.

## Verification

- ESPHome 2026.7.0 Factory S3 and Bridge configurations validated and compiled.
- S3 image: 54.5% RAM, 72.5% flash.
- Bridge image: 42.1% RAM, 64.4% flash.
- Home Assistant integration tests pass against Home Assistant 2026.7.4.
- Python lint, formatting, compilation, shell syntax, manifests and release
  checksums passed.

## Public artifact checksums

```text
27caa43074ad9b5d82a8ba726a0d87cde49cee81d88acfb3476802996a4691ba  s3/passion-wave-rotaryknob-s3-3.0.0-beta.12.factory.bin
79362dcb7818a682122edafee76a1be97314e916e23aec24292707a38d324a2b  s3/passion-wave-rotaryknob-s3-3.0.0-beta.12.ota.bin
c4a4127145af91468e0e3c31b46df9f5b5c0010db085aad8dd6e09c6e8bfffaa  esp32/passion-wave-rotaryknob-esp32-3.0.0-beta.12.factory.bin
e74ed5d47404abd6eccdcd8bbd3cef48818241ad8a5245ac281c9b0588a0c68b  esp32/passion-wave-rotaryknob-esp32-3.0.0-beta.12.ota.bin
```

Known issues and remaining physical acceptance gates are documented in
`docs/known-issues.md`.
