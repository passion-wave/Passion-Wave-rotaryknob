# Firmware and integration 3.0.1-beta.2

Release description: `atomic-media-presentation`

3.0.1-beta.2 keeps title, artist and cover synchronized across the media page
and cover screensaver. It also removes the thin white side seams from the
weather screensaver. The release is coordinated across the Home Assistant
integration, the ESP32 Bridge and the ESP32-S3 display firmware.

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

## Root cause

Music Assistant can publish state, title, artist and artwork through several
rapid `state_changed` events. The previous integration forwarded every
transitional event, and the Bridge then sent each presentation field as a
separately visible UART message. A track transition could therefore combine a
new player state with the previous title or cover. The cover screensaver also
had an additional fallback label path, and the library-start dialog could
overwrite that label before the player confirmed playback.

## Verification

- Home Assistant 2026.7.4 and 2026.8.2: 79 tests and four subtests pass per
  version.
- AwesomeVersion orders `3.0.1-beta.2` above both integration
  `3.0.1-beta.1` and firmware `3.0.0-beta.19`.
- All six factory and managed ESPHome configurations validate and compile with
  ESPHome 2026.7.0.
- Factory S3: 52.9% RAM, 71.8% flash.
- Factory Bridge: 40.4% RAM, 63.0% flash.
- Both managed S3 profiles: 52.8% RAM, 71.7% flash.
- Both managed Bridge profiles: 40.3% RAM, 62.8% flash.
- Both generated manifests advertise `3.0.1-beta.2` and contain the matching
  OTA MD5, immutable release URL and chip family.
- The four public artifacts match `release/public/SHA256SUMS`.

## Public artifact checksums

```text
928ced02d5b346e702b93f970ba8b1686aaa5f8fce922337e155dc46a9fb55c0  s3/passion-wave-rotaryknob-s3-3.0.1-beta.2.factory.bin
76de3b8d1622c09f2d5ee3bbdf7d67dc040e2608c43670e0fbc69ffcf80dff16  s3/passion-wave-rotaryknob-s3-3.0.1-beta.2.ota.bin
7cc0e9e0be2b373e55bed4bfe0f9441d2ed731bbbfb7af2dc5f41933e23f8696  esp32/passion-wave-rotaryknob-esp32-3.0.1-beta.2.factory.bin
2ca646ea59fd8b1a4a7e125c2648f1292a1f26996a023072df62f12b22ab5328  esp32/passion-wave-rotaryknob-esp32-3.0.1-beta.2.ota.bin
```

## Live acceptance on Timo

1. Install integration 3.0.1-beta.2 and restart Home Assistant.
2. Start Timo's single PassionWave firmware update from 3.0.0-beta.19.
3. Confirm the update remains active while Bridge and S3 install sequentially.
4. Confirm both processors reconnect as 3.0.1-beta.2, phase becomes `complete`
   and the logical update entity returns to `off` with no error.
5. Start and skip several Music Assistant tracks. Confirm the media page and
   cover screensaver always show the same current title and artist, without the
   previous cover flashing during the transition.
6. Open the weather screensaver and confirm the background reaches both side
   edges without a white vertical seam.
