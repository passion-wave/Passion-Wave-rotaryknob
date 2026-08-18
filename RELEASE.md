# Firmware 3.0.0-beta.19 and integration 3.0.1-beta.1

Release description: `observable-ota`

Beta.19 repairs the Home Assistant update interaction observed on Marco and
makes the complete two-processor OTA chain observable. It includes all startup
and media-title fixes from Beta.18.

Integration 3.0.1-beta.1 accepts both the historical `Rotaryknob …` and
current `RotaryKnob …` ESPHome registry casing, removes a thread-unsafe state
callback and reports the manual recovery requirement immediately when a clean
pre-Beta.19 device has no native recovery update entity. It also prefers the
live, enabled ESPHome entity when an OTA has left an unavailable registry
duplicate with the same firmware contract name. This removes the false S3
problem state observed after Marco's Beta.16 to Beta.19 transition.

The integration version advances to the HACS-comparable 3.0.1-beta.1 line.
HACS/AwesomeVersion did not order the earlier multi-part prerelease suffixes
`beta.19.1` and `beta.19.2`, so their releases were known internally but did
not turn the Home Assistant update entity on.

## Customer-visible changes

- The update dialog remains in progress until Bridge and S3 have both
  reconnected with the target version or a concrete error is returned.
- Home Assistant displays combined progress across Bridge and S3.
- Each processor refreshes its public HTTP manifest immediately before
  installation instead of relying on the six-hour polling cache.
- Manifest download failure, target mismatch, non-installable image and OTA
  download/flash error code are returned without waiting for the generic
  five-minute reconnect timeout.
- The upgrade from pre-Beta.19 firmware uses and refreshes a hidden native
  ESPHome update entity when that legacy entity exists. Clean Beta.16 factory
  devices without it now receive an immediate, actionable one-time ESPHome OTA
  recovery message instead of another five-minute reconnect timeout.
- The architecture document contains a protocol-labelled Mermaid sequence for
  Home Assistant service dispatch, encrypted ESPHome Native API, HTTPS
  manifest/binary transfer, MD5 verification and processor reconnect.

## Verification

- Home Assistant 2026.7.4 and 2026.8.2: 74 tests and four subtests pass per
  version.
- All six factory and managed ESPHome configurations validate and compile with
  ESPHome 2026.7.0.
- Factory S3: 52.8% RAM, 71.7% flash.
- Factory Bridge: 40.3% RAM, 63.0% flash.
- Both managed S3 profiles: 52.7% RAM, 71.7% flash.
- Both managed Bridge profiles: 40.2% RAM, 62.8% flash.
- Both generated manifests advertise Beta.19 and contain the matching OTA MD5,
  immutable release URL and chip family.
- The four public artifacts match `release/public/SHA256SUMS`.

## Public artifact checksums

```text
702d1fd09dacf85a92112d2f2b613371a7bbb1541d4df4ad9bc3a6642ffa2ac6  s3/passion-wave-rotaryknob-s3-3.0.0-beta.19.factory.bin
4e8e5fa35e1c8c49a673852b0d0e4589f4332a023c56e0d773eac229ca98f654  s3/passion-wave-rotaryknob-s3-3.0.0-beta.19.ota.bin
938eb1eda0a90ae8d409f49e607725f42dcb426453ca9c26d8996397194b090e  esp32/passion-wave-rotaryknob-esp32-3.0.0-beta.19.factory.bin
7e41e788b4943b15d40d809ca0da80f6db84c2e2f1f6a1b7c8f8829018c7e88a  esp32/passion-wave-rotaryknob-esp32-3.0.0-beta.19.ota.bin
```

## Live acceptance

1. Install integration 3.0.1-beta.1 and restart Home Assistant.
2. Start Marco's single PassionWave firmware update from Beta.16.
3. Confirm the update remains visibly active and Bridge is installed before
   S3.
4. Confirm both processors reconnect as Beta.19, phase becomes `complete`,
   target and error clear, and no native duplicate update remains visible.
5. Repeat one no-op/current-version check or the next release update to verify
   the new `checking` → `manifest_ready` → `ota_progress` diagnostics.
