# Firmware and integration 3.0.0-beta.17

Beta.17 consolidates the public product and hosting contract. Customer-facing
text now uses `RotaryKnob`; lowercase paths, firmware filenames, project IDs,
integration domains and entity IDs remain stable technical identifiers. All
public website, installer and OTA-manifest references use the canonical
`https://www.passion-wave.com` domain.

Release description: `canonical-domain-and-product-name`

## Status

Reproducibly built release candidate. Automated integration, configuration,
firmware, manifest, checksum and website checks pass. Cloudflare production,
custom-domain, OTA and physical-device verification remain release gates; this
candidate must not be promoted before they are completed.

## Customer-visible changes

- The product is consistently displayed as `RotaryKnob` in Home Assistant,
  ESPHome, the factory WLAN, setup dialogs, firmware manifests and website.
- The public installer, documentation, support link and firmware update sources
  use `https://www.passion-wave.com`.
- Cloudflare Workers is the sole public production and preview platform.
- The Beta.16 consolidated update transaction remains unchanged: Bridge first,
  verified reconnect, S3, verified reconnect.
- Empty light positions, S3-based product identity, queued offline updates and
  the local three-part version display from Integration 3.0.0-beta.16.5 remain
  included.

## Verification

- Home Assistant 2026.7.4 and 2026.8.2 integration suites: 56 tests and four
  subtests passed per version.
- Factory S3 and Bridge configurations validated and compiled with ESPHome
  2026.7.0.
- Factory S3: 52.6% RAM, 71.7% flash.
- Factory Bridge: 40.1% RAM, 62.8% flash.
- Both managed S3 profiles: 52.5% RAM, 71.6% flash.
- Both managed Bridge profiles: 40.0% RAM, 62.6% flash.
- Both generated manifests use the same Beta.17 version, exact `RotaryKnob`
  display names, chip family, OTA MD5 and immutable GitHub release URL.
- Firmware files match the generated SHA-256 inventory.
- Physical update and clean-install verification on Marco and Timo is pending.

## Public artifact checksums

```text
cb4d2efceae01cd8213af99b4cdd7bb97d918f1544d1508fa1ebf290fef760ed  s3/passion-wave-rotaryknob-s3-3.0.0-beta.17.factory.bin
b9e83cd04f51ec9213b0571f91dfd5281a07586441b5a3896be53db86b2c6f29  s3/passion-wave-rotaryknob-s3-3.0.0-beta.17.ota.bin
2ad3dd1f74c1d189f65dd405178e6929738ee60fab54f1a521b0adda5bbf93f8  esp32/passion-wave-rotaryknob-esp32-3.0.0-beta.17.factory.bin
2f351bb462c5ba0d121ac483f99d411ee155c1d6fbb42375b22e924060942961  esp32/passion-wave-rotaryknob-esp32-3.0.0-beta.17.ota.bin
```

## Known limitation

The playlist-start failure can still leave the media picker open and thereby
block the screensaver. This unrelated defect remains explicitly open.
