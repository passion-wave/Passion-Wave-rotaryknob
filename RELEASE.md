# Firmware and integration 3.0.1-beta.4

Release description: `reconnect-media-rehydration`

3.0.1-beta.4 keeps title, artist and cover synchronized across the media page
and cover screensaver. It also removes the thin white side seams from the
weather screensaver. The release is coordinated across the Home Assistant
integration, the ESP32 Bridge and the ESP32-S3 display firmware. In addition,
it closes the update-completion race found during the live Beta.2 installation.
It also rehydrates the complete runtime presentation whenever the Bridge API
reconnects, including the sequential Bridge/S3 reboot during an update.

## Customer-visible changes

- Weather backgrounds are centered at 102% scale without interpolation, so
  they extend beyond every edge of the 360×360 display.
- The selected Home Assistant media player is the only title, artist and cover
  authority. The media page and cover screensaver read the same S3 caches.
- Home Assistant coalesces the short burst of Music Assistant state and
  metadata events for 250 ms before sending a complete runtime snapshot.
- Bridge and S3 use a sequence-bound presentation transaction:
  `MEDIA_PRESENTATION_BEGIN`, title, artist, cover URL and
  `MEDIA_PRESENTATION_COMMIT`.
- The S3 exposes the new presentation only after all three fields are complete
  and the session and sequence match. The previous decoded cover is invalidated
  before the new title becomes visible.
- Starting a playlist or track no longer writes its library label optimistically
  into the authoritative runtime title. Only the actual player state can update
  the displayed title and artist.
- The new UART capability remains rolling-update compatible: older S3 firmware
  ignores the new boundary frames and consumes the unchanged payload frames.
- Both processors wait for a fresh, installable manifest state for up to 60
  seconds before starting OTA.
- Home Assistant accepts the processor's fresh `checking` state, allows up to
  90 seconds for OTA startup and refreshes stale ESPHome device metadata after
  reconnect. A fast S3 reboot can no longer leave a completed update displayed
  as failed.
- A Bridge command-entity transition from unavailable to available immediately
  retries a complete authoritative runtime snapshot. The update coordinator
  also requests this rehydration after the Bridge firmware reconnects.

## Root cause

Music Assistant can publish state, title, artist and artwork through several
rapid `state_changed` events. The previous integration forwarded every
transitional event, and the Bridge then sent each presentation field as a
separately visible UART message. A track transition could therefore combine a
new player state with the previous title or cover. The cover screensaver also
had an additional fallback label path, and the library-start dialog could
overwrite that label before the player confirmed playback.

During the Beta.2 live installation, the S3 completed its OTA and rebooted
between the blocking ESPHome action and Home Assistant's status observer. The
device registry still exposed the previous version, so the logical updater
timed out even though the processor already ran the target. Beta.3 recognizes
the fresh checking/reconnect path and reloads endpoint metadata at bounded
intervals before deciding that an update failed.

The Beta.3 live acceptance then exposed a second reboot-order race: Home
Assistant sent the current idle-player presentation before the updated Bridge
rebooted. The Bridge lost that volatile cache, so the subsequently rebooted S3
received clock and device data but retained its fallback `Keine Wiedergabe`
until the next player event. Beta.4 observes the Bridge API reconnect and
re-sends the selected player's complete title, artist and cover transaction.

## Verification

- Home Assistant 2026.7.4 and 2026.8.2: 83 tests and four subtests pass per
  version.
- AwesomeVersion orders `3.0.1-beta.4` above both integration
  `3.0.1-beta.1` and firmware `3.0.0-beta.19`.
- All six factory and managed ESPHome configurations validate and compile with
  ESPHome 2026.7.0.
- Factory S3: 52.9% RAM, 71.8% flash.
- Factory Bridge: 40.4% RAM, 63.0% flash.
- Both managed S3 profiles: 52.8% RAM, 71.7% flash.
- Both managed Bridge profiles: 40.3% RAM, 62.8% flash.
- Both generated manifests advertise `3.0.1-beta.4` and contain the matching
  OTA MD5, immutable release URL and chip family.
- The four public artifacts match `release/public/SHA256SUMS`.

## Public artifact checksums

```text
79e108113fb144ed5ed2dda4ec9b0d6d844dff42953b493fb605e3d186997f2c  s3/passion-wave-rotaryknob-s3-3.0.1-beta.4.factory.bin
52d6633e0acd6dd971751020fa390759e1a0a72328526b002ccdab4dacba9322  s3/passion-wave-rotaryknob-s3-3.0.1-beta.4.ota.bin
9dfd9d08abeaf109a470ecaed7ef332ba322d626704621145dfe6e808420c4b5  esp32/passion-wave-rotaryknob-esp32-3.0.1-beta.4.factory.bin
e3652c627c6ac89b0f985d713439de4d8ded4b9dac2702965755ec86b20d1c83  esp32/passion-wave-rotaryknob-esp32-3.0.1-beta.4.ota.bin
```

## Live acceptance on Timo

1. Install integration 3.0.1-beta.4 and restart Home Assistant.
2. Start Timo's single PassionWave firmware update from 3.0.1-beta.3.
3. Confirm the update remains active while Bridge and S3 install sequentially.
4. Confirm both processors reconnect as 3.0.1-beta.4, phase becomes `complete`
   and the logical update entity returns to `off` with no error.
5. Start and skip several Music Assistant tracks. Confirm the media page and
   cover screensaver always show the same current title and artist, without the
   previous cover flashing during the transition.
6. Open the weather screensaver and confirm the background reaches both side
   edges without a white vertical seam.
7. Leave the selected player idle with metadata, reboot both processors through
   the coordinated update, and confirm the S3 automatically restores the same
   title, artist and cover without waiting for a new player event.
