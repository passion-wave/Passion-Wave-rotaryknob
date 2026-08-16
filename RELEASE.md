# Version 3.0.0-beta.15

Release description: `responsive-power-runtime`

## Status

Coordinated public prerelease for the Home Assistant integration and both
Rotaryknob processors. S3 and Bridge images are built from this source and must
always be installed together through the single PassionWave firmware update.

## Customer-visible changes

- The supported update path remains entirely in Home Assistant: update the
  PassionWave integration through HACS, restart Home Assistant and install the
  one `PassionWave Rotaryknob Firmware` update.
- The updater installs the Bridge first, verifies its reconnect, then installs
  and verifies the S3. A failed Bridge phase stops before the display processor
  is touched.
- On battery, both processors now enter connected Wi-Fi modem sleep after a
  three-second idle window. External power and active interaction retain the
  lowest-latency Wi-Fi mode.
- Encoder input, actionable inter-processor frames and S3 image transfers
  immediately hold or restore the responsive Wi-Fi mode.
- With no playback, timer or alarm, the S3 deep-sleep point is shortened from
  90 to 75 seconds after activity; the existing display-off point remains 60
  seconds.
- CPU frequency scaling and automatic light sleep remain disabled until UART,
  visual and latency acceptance has been measured on complete hardware.
- Factory and both maintained managed profiles use the same Beta.15 runtime
  policy and coordinated version.

## Coordinated customer update

1. Install PassionWave `3.0.0-beta.15` through HACS and restart Home Assistant.
2. Open the device page of the logical PassionWave Rotaryknob.
3. Open `PassionWave Rotaryknob Firmware` and press **Install** once.
4. Wait for Bridge update and verified reconnect.
5. Wait for S3 update and verified reconnect.
6. Confirm that the integration, Bridge and S3 all report `3.0.0-beta.15`.

Do not install the two hidden ESPHome transport updates separately during the
normal customer flow. They remain recovery transports only.

## Verification

- Public Factory S3 and Bridge configurations validated and compiled with the
  pinned ESPHome release environment.
- All four maintained managed profiles validated and compiled from the same
  source generation.
- Home Assistant integration tests, Python checks, shell syntax, manifests,
  firmware checksums and website validation passed.
- The release process did not directly flash either physical Rotaryknob.
- Physical Beta.15 update, power and long-duration acceptance remains a
  post-publication customer-process check and is not claimed as completed.

## Public artifact checksums

The final SHA-256 values below are generated from the release build and copied
unchanged to the website and the cross-repository release record.

```text
8baa584ada20da273a1fc0e301bab3573880f0e9cbad5246650ce01a2b4d16d0  s3/passion-wave-rotaryknob-s3-3.0.0-beta.15.factory.bin
76532eb8458347b92e8f11e285602c18c66cfac1550c3aa0dae7a4d85b23035b  s3/passion-wave-rotaryknob-s3-3.0.0-beta.15.ota.bin
0bc0ab35450f48bebc4fb31599bc784e18a468c584e315708dc369c7d6840d44  esp32/passion-wave-rotaryknob-esp32-3.0.0-beta.15.factory.bin
2bbccf59a015d2a7460eee667190b6ecec53dd26358e8c163f28c55be962b10d  esp32/passion-wave-rotaryknob-esp32-3.0.0-beta.15.ota.bin
```

## Known limitation

The previously diagnosed media-selection failure can leave the media picker
open after a rejected playlist-track start. Because an open media picker
intentionally blocks idle mode, the weather screensaver will not start until
the picker is closed. Beta.15 does not silently change that behavior.

All remaining physical acceptance gates are tracked in
`docs/known-issues.md`.
