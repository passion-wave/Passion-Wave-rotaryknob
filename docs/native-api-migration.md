# MQTT-free Native API migration

Status: published as `3.0.0-beta.0`; physical clean-device acceptance pending.

Because the device no longer accepts the former transport, publish this change
only as an explicitly marked V3 prerelease until both chips of the physical
device pass acceptance. Do not silently replace a `2.1.x` artifact with this
build.

## Decision

The new firmware intentionally provides no backward-compatible MQTT path.
Both processors must be updated as one coordinated pair. Retained
`passion_wave/media/*` messages, MQTT credentials and MQTT discovery copies are
ignored because the MQTT component is no longer compiled.

This reduces DNS connections, authentication failure loops, duplicated entity
copies, parsing callbacks and recovery state. It also removes the original
failure in which a public Factory image attempted anonymous access to a broker
that correctly rejected it.

## Runtime chain

```text
Display/encoder (ESP32-S3)
  -> bounded 2 Mbit/s UART request
Bridge (classic ESP32)
  -> encrypted ESPHome Native API action
Home Assistant / Music Assistant
  -> bounded response
Bridge cache
  -> bounded UART page
Display
```

- Playlists, radio and podcasts: `passion_wave.get_library`.
- Playlist tracks: `passion_wave.get_playlist_tracks`.
- Floorplan revision and URL:
  `pyscript.passion_wave_floorplan_revision`.
- Radar metadata and asset URL: Home Assistant state subscriptions.
- Images: downloaded only by the Bridge; the S3 receives bounded image chunks.

The UI requests the next library page before the visible end. Five remaining
rows are the prefetch threshold. A request-in-flight guard prevents duplicates,
and the previous complete page remains visible during a short API interruption.

## Home Assistant prerequisites

1. Copy `custom_components/passion_wave` to
   `/config/custom_components/passion_wave`.
2. Restart Home Assistant.
3. Add one **PassionWave** Config Entry per physical Rotaryknob.
4. Select its Bridge registration entity, Music Assistant instance and Music
   Assistant player.
5. Keep “Allow the device to perform Home Assistant actions” enabled for the
   Bridge ESPHome integration entry.

The helper script uses `media_player.browse_media` inside Home Assistant and
returns only the requested slice. It needs neither a Music Assistant API token
nor a copied encryption key.

## Coordinated migration

Do not update only one processor and leave the pair in mixed mode.

1. Back up the current ESPHome and Home Assistant configuration.
2. Install/reload the PassionWave integration and create its Config Entry.
3. Build both images from the same release tag.
4. Update the Bridge first and wait until its encrypted API is connected.
5. Update the S3.
6. Open the PassionWave Config Entry once and verify that the Bridge
   registration entity contains its Config Entry ID.
7. Verify playlist, radio and podcast bootstrap; scroll until a page prefetch
   occurs; open one playlist and repeat the paging test for tracks.
8. Verify radar and floorplan invalidation.
9. Only after acceptance, remove the old MQTT automation, retained
   `passion_wave/media/*` messages and obsolete MQTT credentials.

Rollback requires rolling back both MCU images together. The new S3 does not
wake a direct MQTT fallback when the Bridge is unavailable.

## Further slimming

Recommended now:

- remove the MQTT broker requirement from customer onboarding;
- keep all network ownership on the Bridge;
- retain page limits and the five-row prefetch threshold;
- keep photos cacheable for a long time, but release radar and floorplan image
  buffers shortly after decoding because those assets must remain current.

Not recommended:

- returning a complete large playlist through `browse_media` to the ESP32;
- moving media parsing back to the S3;
- combining S3 and classic ESP32 binaries, because the chips and roles differ;
- removing PSRAM image buffers without measurement, because that risks display
  stalls without improving the hot media path.
