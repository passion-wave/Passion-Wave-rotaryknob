# Guided Installation Concept

The target public installation path is a guided browser flow for a newly bought
device.

## Customer Flow After Purchase

The public wording should stay as short as possible:

1. Connect the Rotaryknob by USB.
2. Open `https://www.passion-wave.com/install`.
3. Erase, flash and provision the detected S3 as `PassionWave Rotaryknob`.
4. Unplug, reverse USB-C and reconnect.
5. Erase, flash and provision the detected ESP32 as `PassionWave Rotaryknob Bridge`.
6. Press `Open Home Assistant`.
7. Approve both discovered PassionWave processor endpoints for the one
   Rotaryknob. Home Assistant 2026.7 or newer generates, provisions and stores
   a unique API encryption key for each endpoint; the customer does not enter
   or copy a key.
8. Select media, weather and optional lights from Home Assistant pickers.

The customer should never copy entity IDs. Home Assistant owns entity discovery,
so the blueprint selectors list the compatible `media_player` and `light`
entities directly.

## Simplicity Rules

- One public start page: `passion-wave.com/install`.
- One visible primary action per stage.
- No copied entity IDs.
- No manual YAML editing for normal buyers.
- After writing completes, the browser's `Next` action opens Wi-Fi
  provisioning before the website allows the next processor stage.
- Home Assistant choices are asked inside Home Assistant because it knows the
  user's entities.
- Advanced ESPHome, secrets and factory-binary details stay in maintainer docs,
  not in the buyer flow.

## What Can Be Automated

- Browser flashing through ESP Web Tools.
- Wi-Fi provisioning over Improv Serial.
- ESPHome discovery in Home Assistant.
- Home Assistant integration setup through a My link.
- Media player, weather and light selection through a config flow.
- Persistent storage of the chosen targets on the ESPHome device.

## What Still Requires Confirmation

Home Assistant must ask the local user to confirm device setup, blueprint import
and automation creation. That is intentional security behavior because a public
website cannot be allowed to configure a private Home Assistant installation
without user approval.

## Public Factory Firmware Requirements

The website installer must consume two sanitized factory manifests:

```text
https://www.passion-wave.com/firmware/rotaryknob/s3/manifest-3.0.0-beta.2.json
https://www.passion-wave.com/firmware/rotaryknob/esp32/manifest-3.0.0-beta.2.json
```

Each image must be built from a public factory configuration with:

- no private Wi-Fi credentials;
- no private API encryption key;
- no private OTA password;
- no MQTT component or broker credentials;
- `name_add_mac_suffix` enabled;
- `api.encryption` without a compiled key plus a bounded `provisioning` window;
- `improv_serial` enabled;
- `captive_portal` enabled;
- `dashboard_import` enabled for ESPHome adoption.
- a first-adoption guard that keeps the S3 discoverable until Home Assistant
  has connected once.
- no Improv `next_url`; the website owns stage progression.

Development builds with private `secrets.yaml` values must never be published
as website installer assets.

## Current Implementation Status

- The website contains a five-stage `/install/` wizard with separate ESP Web
  Tools install buttons for the S3 and classic ESP32.
- The website contains the chip-specific manifests
  `/firmware/rotaryknob/s3/manifest-3.0.0-beta.2.json` and
  `/firmware/rotaryknob/esp32/manifest-3.0.0-beta.2.json`.
- Both production factory binaries are published and their SHA-256 sums match
  the firmware repository's `release/public/SHA256SUMS`.
- The device defaults blueprint contains Home Assistant entity selectors for
  all `media_player` and `light` entities.
- The firmware stores selected media and light targets persistently and shows
  Wi-Fi, Home Assistant and IP status in settings.
- Each manifest declares exactly one matching chip family. The wizard explains
  the USB-C reversal and links to Home Assistant after both stages.
- Public factory buttons force clean installation even if an older Passion
  Wave firmware identifies as the same project. A separate bridge button
  reopens Improv without reflashing if serial reconnection fails.
- Pairing both ESPHome endpoints into one logical Home Assistant product and the
  planned no-code `passion_wave` config flow are not implemented.

The two-chip browser installer is implemented, but the complete retail
onboarding remains a release candidate until physical clean-device validation
and the unified Home Assistant config flow are complete. See
[Customer product architecture](customer-product-architecture.md) for the
release design and acceptance stages.
