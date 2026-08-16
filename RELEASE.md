# Version 3.0.0-beta.16

Release description: `consolidated-update-contract`

## Status

Automated release candidate for the Home Assistant integration and both
Rotaryknob processors. Public artifacts are reproducibly built. Physical
installation and clean Home Assistant onboarding remain explicit manual gates.

## Customer-visible changes

- One physical Rotaryknob exposes exactly one PassionWave firmware update.
- The S3 and Bridge ESPHome update components are internal and no longer
  appear as separate customer updates after Beta.16 is installed.
- One click creates a persistent transaction. It waits up to 24 hours for a
  sleeping processor and survives a Home Assistant restart.
- The safe sequence remains Bridge → verified reconnect → S3 → verified
  reconnect. Success is reported only after both installed versions match.
- New onboarding derives the logical product identity only from the selected
  S3 MAC. Bridge registration IDs can no longer identify another device.
- Legacy identity migration is deliberately omitted. Existing beta devices
  may be removed and onboarded again without preserving old logical entries.
- The local Settings page contains a `Versionen` item showing the running S3,
  Bridge and PassionWave integration versions. Missing remote information is
  displayed as `nicht verfügbar`.

## Beta.15 transition

The Beta.16 integration can use the two Beta.15 ESPHome update sources once to
install Beta.16. After both processors reconnect with Beta.16, their obsolete
registry update entities are disabled and all later releases use only the
internal firmware actions.

## Verification

- Home Assistant 2026.7.4 and 2026.8.2 integration suites: 47 tests and four subtests passed per version.
- Factory S3 and Bridge configurations validated and compiled with ESPHome
  2026.7.0.
- Marco and Timo managed S3 and Bridge profiles validated and compiled.
- Factory S3: 52.6% RAM, 71.7% flash.
- Managed S3: 52.5% RAM, 71.6% flash.
- Managed Bridge: 40.0% RAM, 62.6% flash.
- Physical update, Settings rendering, clean onboarding and offline resume are
  not claimed until the manual gates are completed.

## Public artifact checksums

```text
06791ffc529d39ab40d5fd9954353c65b4cf38142cc3526f6404ad6a598e0f74  s3/passion-wave-rotaryknob-s3-3.0.0-beta.16.factory.bin
2b77d125b4afd2e28df619722c5b4c5f3b5abea29bd9019b27eb7f46965cc49c  s3/passion-wave-rotaryknob-s3-3.0.0-beta.16.ota.bin
12a44683c80082d941616ad5a0fdc3287079be81e002c1649697649ede0487f2  esp32/passion-wave-rotaryknob-esp32-3.0.0-beta.16.factory.bin
8bab06949d6f263557fc600ba068e96e30d9790930509ee83bb19e61fee03b79  esp32/passion-wave-rotaryknob-esp32-3.0.0-beta.16.ota.bin
```

## Known limitation

The playlist-start failure can still leave the media picker open and thereby
block the screensaver. This unrelated defect remains explicitly open.
