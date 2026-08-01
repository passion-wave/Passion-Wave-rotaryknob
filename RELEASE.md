# Version 3.0.0-beta.11

Release description: `screensaver-media-and-discovery-hardening`

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
a9cf470e17920afc0f9e0773f4155c7bc16c8cf4fe526d7bbc1085958a13ad81  s3/passion-wave-rotaryknob-s3-3.0.0-beta.11.factory.bin
4d44e5800924e3259b7f50b280372c3bd05c33cd78dca65b8ade86b7b6080407  s3/passion-wave-rotaryknob-s3-3.0.0-beta.11.ota.bin
8be5b178db9ec25b3c97f7793a12364670b37773149fd1b3ee891acbdc093c07  esp32/passion-wave-rotaryknob-esp32-3.0.0-beta.11.factory.bin
a336fc28a13703ed92b8562880492cbc12600353307e782a868034a00e275b98  esp32/passion-wave-rotaryknob-esp32-3.0.0-beta.11.ota.bin
```

Known issues and remaining physical acceptance gates are documented in
`docs/known-issues.md`.
