# Version 3.0.0-beta.10

Release description: `single-device-discovery-and-coordinated-update`

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
- 13 Home Assistant integration tests passed against Home Assistant 2026.7.4.
- Python lint, formatting, compilation, shell syntax, manifests and release
  checksums passed.

## Public artifact checksums

```text
5536427b231a3ab0d1b35124b583158b10099a861fb543ce9d178d09e13baee5  s3/passion-wave-rotaryknob-s3-3.0.0-beta.10.factory.bin
ff0cdb62b9fae7ee5172a9c1b4d309c3fb3bc964b1d0b7d34aa47451592f464c  s3/passion-wave-rotaryknob-s3-3.0.0-beta.10.ota.bin
de04693b9dfeddc03323caefbc667a58e3615fbc99bd1cd504538d9b39cfd6f8  esp32/passion-wave-rotaryknob-esp32-3.0.0-beta.10.factory.bin
c90417435820f76eac19f1c2402237df62da0d7055854868c6dbdb92eecbbb02  esp32/passion-wave-rotaryknob-esp32-3.0.0-beta.10.ota.bin
```

Known issues and remaining physical acceptance gates are documented in
`docs/known-issues.md`.
