# Firmware and integration 3.0.0-beta.18

Beta.18 repairs the startup and media-presentation chain observed on the live
RotaryKnobs. It also documents the complete playlist-selection, Music
Assistant, AirPlay and display-feedback architecture with protocol-labelled
Mermaid diagrams.

Release description: `startup-media-runtime`

## Status

Reproducibly built release candidate. Automated integration, configuration,
firmware, manifest and checksum checks pass. The source-level live diagnosis
was performed against both existing RotaryKnobs; physical Beta.18 OTA,
display/startup acceptance and public website verification remain release
gates until the artifacts have been published and installed.

## Customer-visible changes

- A current title received from the configured Home Assistant media player is
  rendered on the RotaryKnob immediately instead of remaining on `Keine
  Wiedergabe`.
- Reasserting an unchanged player target no longer clears a newer title from
  the S3 presentation cache.
- If the player is `playing` but the title is missing, the S3 requests a new
  authoritative Bridge snapshot after ten seconds.
- Every HELLO snapshot sends `TIME_STATE` first, removing the previous wait for
  the Bridge's ten-second maintenance interval.
- New disabled-by-default diagnostics expose UI-ready time, clock-ready time,
  startup phase and the title actually read back from the LVGL label.
- The periodic Home Assistant reconciliation writes targets before it sends
  the authoritative runtime snapshot, so the snapshot is always the final
  presentation state.
- Architecture and sequence diagrams identify GPIO/PCNT, UART v3 with
  COBS/CRC, encrypted ESPHome Native API, Music Assistant JSON WebSocket and
  negotiated RAOP/AirPlay transport.

## Verification

- Live diagnosis on 2026-08-18: the selected Home Assistant player, Bridge and
  S3 runtime diagnostics agreed on playing state, title, artist and cover URL;
  this isolated the defect to S3 cache/render ordering.
- Home Assistant 2026.7.4 and 2026.8.2 integration suites: 62 tests and four
  subtests passed per version.
- Factory S3 and Bridge configurations validated and compiled with ESPHome
  2026.7.0.
- Factory S3: 52.7% RAM, 71.7% flash.
- Factory Bridge: 40.1% RAM, 62.8% flash.
- Both managed S3 profiles: 52.6% RAM, 71.6% flash.
- Both managed Bridge profiles: 40.0% RAM, 62.6% flash.
- Both generated manifests use the same Beta.18 version, chip family, OTA MD5
  and immutable GitHub release URL.
- Firmware files match the generated SHA-256 inventory.

## Public artifact checksums

```text
345b8a08000ca9efa9f723a03e82ed04aecdd954b1301e40cc1d9ff1efa46eb1  s3/passion-wave-rotaryknob-s3-3.0.0-beta.18.factory.bin
89ed30e8aca0111113a0c70090520e844d1a933bb00d308f1169afb00e594fea  s3/passion-wave-rotaryknob-s3-3.0.0-beta.18.ota.bin
8181b5d87982e1552f6fa69b65a3b120a1ad35a1494920beb270247bb1ecb89f  esp32/passion-wave-rotaryknob-esp32-3.0.0-beta.18.factory.bin
389db52acd378cc3b6c979e56ba93f9f640b1187e09e58696f8c99e3190f8806  esp32/passion-wave-rotaryknob-esp32-3.0.0-beta.18.ota.bin
```

## Physical acceptance after OTA

1. Cold-start Bridge and S3 and record `RotaryKnob UI Ready Time` plus
   `RotaryKnob Clock Ready Time`.
2. Confirm that a valid clock is visible before the 30-second screensaver
   timeout.
3. Start a playlist and let at least three tracks change on the configured
   player.
4. Confirm that Home Assistant `media_title`, `RotaryKnob Media Runtime Title`,
   `RotaryKnob Rendered Media Title` and the visible label agree throughout.
5. Confirm zero new UART/COBS/CRC errors and a connected Bridge/S3 link.

## Known limitation

The unrelated failure path in which a rejected playlist start leaves the media
picker open remains separately tracked. Beta.18 addresses successful playback
state and title propagation, not that popup error path.
