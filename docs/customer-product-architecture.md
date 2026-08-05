# Customer product architecture

## Goal

A buyer with no ESPHome or YAML knowledge should be able to install an
unflashed Passion Wave Rotaryknob with a USB data cable, a Chromium-based
desktop browser and Home Assistant.

With the current board this is feasible as a guided **two-stage** install. It
cannot honestly be presented as one physical flash: reversing the USB-C plug
selects the other processor.

Throughout this documentation, **device** means one physical Rotaryknob with
two chips. **Endpoint** means one chip's independently addressable ESPHome
connection. A customer installs two endpoints but owns and configures one
product device. Additional Rotaryknobs repeat the same isolated two-endpoint
model.

## Recommended repository boundaries

### Passion-Wave-rotaryknob

Public, versioned product source:

```text
esphome/
  packages/
    common.yaml
    s3-display.yaml
    esp32-bridge.yaml
  factory/
    rotaryknob-s3.factory.yaml
    rotaryknob-esp32.factory.yaml
  product/
    rotaryknob-s3.yaml
    rotaryknob-esp32.yaml
components/
home_assistant/
  custom_components/passion_wave/
tests/
release/
  manifest-s3.json
  manifest-esp32.json
```

Factory profiles contain no private credentials, use unique MAC-suffixed node
names, support serial Wi-Fi provisioning and expose dashboard adoption
metadata. Product packages are immutable per release tag.

### Passion-Wave-web

Public customer-facing installer and help:

- compatibility check for browser, HTTPS and Web Serial;
- large step-by-step UI with exactly one primary action;
- stage 1: identify and flash the S3;
- explicit unplug/reverse/reconnect illustration;
- stage 2: identify and flash the ESP32;
- verify chip type before each write, so images cannot be swapped;
- provision Wi-Fi for each processor and verify both are reachable;
- open Home Assistant through a My link;
- recovery, retry and support diagnostics without exposing command lines.

The website consumes release manifests; it does not build firmware.

### Passion-Wave-control

Private release governance:

- release checklist and supported ESPHome/Home Assistant matrix;
- CI orchestration for both firmware images;
- binary hashes, provenance and optional signing;
- staging-to-production promotion;
- rollback manifests and retained previous release;
- anonymized release notes, support runbooks and privacy review.

### Home Assistant integration

Create `passion_wave` as a UI-configured custom integration first, then pursue
an official Home Assistant integration if distribution volume justifies it.
Its config flow should:

1. discover and pair the S3 and ESP32 by a shared product ID;
2. present them as one logical Passion Wave device;
3. select weather entity, media player, Music Assistant instance and zero to
   four lights through native selectors;
4. configure optional radar, floorplan and photos separately;
5. expose diagnostics, repairs and reconfiguration in the UI.

The integration replaces brittle entity-name searches, copied MQTT credentials,
manual REST commands, setup blueprints, packages and Pyscript as core
requirements. Existing target values are migrated into the Config Entry before
the retired blueprint is removed; beta.12 has completed that migration.

## Buyer journey

1. Scan the QR code on the device or packaging.
2. Open the published PassionWave installer linked from `README.md` in Chrome
   or Edge on desktop.
3. Connect the device and flash the detected ESP32-S3.
4. Enter Wi-Fi and wait for the green S3 verification.
5. Unplug, reverse USB-C, reconnect and flash the detected ESP32.
6. Enter the same Wi-Fi and wait for both processors to be paired.
7. Press **Open Home Assistant** and approve the Passion Wave integration.
8. Choose media, weather and lights from Home Assistant lists.
9. Run the on-device encoder/touch/audio-control check.

No buyer step may require YAML, an entity ID, a broker credential, a terminal,
the ESPHome Device Builder App or a Git checkout.

## Identity and pairing

Both factory images need the same product identifier. The safest production
method is to assign it during manufacturing and encode it as a QR code. If the
device is truly blank, the installer must generate the identifier during stage
1 and pass it to stage 2. That requires a supported writable provisioning field
on both firmwares.

The two ESPHome host names should remain unique, for example:

```text
passion-wave-rotary-<id>-s3
passion-wave-rotary-<id>-bridge
```

The PassionWave Config Entry represents one product device and binds its Bridge
endpoint to the selected Home Assistant and Music Assistant targets. Native
ESPHome management can still show the S3 and Bridge as two technical endpoints;
processor names remain useful for diagnostics and OTA.

## Security and updates

- Never publish shared Wi-Fi, API, MQTT or OTA secrets in a factory image.
- Use local serial provisioning and a captive-portal recovery path.
- Create per-installation credentials during onboarding.
- Pin firmware packages to release tags, never to `main`.
- Publish SHA-256 hashes for both images and retain one rollback release.
- OTA is considered successful only after both processors report the same
  compatible release generation.
- If one processor update fails, keep the protocol backward-compatible and
  show a Home Assistant repair issue instead of partially disabling controls.

ESPHome's creator guidance supports credential-free factory firmware with an
AP/captive portal or Improv Serial, MAC-suffixed names and
`dashboard_import`. See
[Sharing ESPHome devices](https://esphome.io/guides/creators/).
Home Assistant integrations can provide UI-only setup through a
[config flow](https://developers.home-assistant.io/docs/core/integration/config_flow/).

## Commercial recommendation

Selling a completely blank board transfers the riskiest manufacturing step to
the least technical person and doubles it because there are two processors.
The best customer experience is to preflash a minimal, credential-free
bootstrap on both processors and sell the device **unconfigured**, not
unflashed. This preserves privacy while reducing installation to Wi-Fi and
Home Assistant onboarding.

If “unflashed” is a fixed commercial requirement, the two-stage web wizard is
mandatory and should be tested with at least ten first-time users before sale.

## Delivery phases

1. **Release foundation:** split and sanitize both factory profiles; reproducible
   CI builds; publish staging manifests and hashes.
2. **Two-stage installer:** chip detection, connector-orientation guidance,
   provisioning, pair verification and recovery.
3. **No-code Home Assistant:** custom integration config flow and one logical
   device; remove MQTT/REST/YAML from the core path.
4. **Qualification:** clean-install tests, power-loss tests, dual OTA/rollback,
   72-hour endurance and novice usability trial.
