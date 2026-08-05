# Version 3.0.0-beta.14

Release description: `consolidated-customer-runtime`

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
- Normal customer devices expose one combined health signal and keep detailed
  ESPHome diagnostics disabled by default.
- A single Supportdiagnose switch enables the S3 and Bridge diagnostic paths
  together when fault evidence is needed.
- Media and light changes remain event-driven; a complete authoritative state
  is also sent every 15 minutes to heal missed events without rapid polling.
- Media selection uses a latest-command-wins queue: a newer title supersedes a
  pending older request while preserving bounded retries for the active item.
- Tapping the light name cycles directly through the configured lamp slots,
  reducing the number of touch interactions without delaying light controls.

## Coordinated customer update

1. Update the PassionWave integration through HACS and restart Home Assistant.
2. Open the single `PassionWave Rotaryknob Firmware` update entity.
3. Press **Install** once.
4. Wait for Bridge update and verified reconnect.
5. Wait for S3 update and verified reconnect.

The sequence stops before touching the S3 if the Bridge cannot be verified.

## Verification

- ESPHome 2026.7.0 Factory S3 and Bridge configurations validated and compiled.
- S3 image: 52.5% RAM, 71.7% flash.
- Bridge image: 40.0% RAM, 62.7% flash.
- Home Assistant integration tests pass against Home Assistant 2026.7.4.
- Python lint, formatting, compilation, shell syntax, manifests and release
  checksums passed.
- HACS loaded integration Beta 14; both customer devices completed the
  coordinated Bridge → reconnect → S3 update through Home Assistant.
- Both logical updates and all four transport updates report installed and
  latest Beta 14; system status and support diagnostics finish `off`.

## Public artifact checksums

```text
919490d1a8326c1bcdf5a92db1a32770a50c3abb9069262b56f1ea538b5b0c60  s3/passion-wave-rotaryknob-s3-3.0.0-beta.14.factory.bin
5c5eb3762feeb27be9580269e31bc214e8d129004e18a35346b7b6150244a1e1  s3/passion-wave-rotaryknob-s3-3.0.0-beta.14.ota.bin
16965cf796d9c54b3be24f534f6fb3bd9c8f63ef009f1ddbd64376dc6d9f96a6  esp32/passion-wave-rotaryknob-esp32-3.0.0-beta.14.factory.bin
3817017aa0d26629d0089082dc62917b18f29724d53478c7edef9233a76c1da2  esp32/passion-wave-rotaryknob-esp32-3.0.0-beta.14.ota.bin
```

Known issues and remaining physical acceptance gates are documented in
`docs/known-issues.md`.
