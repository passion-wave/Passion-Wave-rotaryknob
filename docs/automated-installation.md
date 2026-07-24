# Guided Installation Concept

The target public installation path is a guided browser flow for a newly bought
device.

## Customer Flow After Purchase

The public wording should stay as short as possible:

1. Connect the Rotaryknob by USB.
2. Open `https://www.passion-wave.com/install`.
3. Flash and provision the detected S3.
4. Unplug, reverse USB-C and reconnect.
5. Flash and provision the detected ESP32.
6. Press `Open Home Assistant`.
7. Approve the discovered Passion Wave product.
8. Select media, weather and optional lights from Home Assistant pickers.

The customer should never copy entity IDs. Home Assistant owns entity discovery,
so the blueprint selectors list the compatible `media_player` and `light`
entities directly.

## Simplicity Rules

- One public start page: `passion-wave.com/install`.
- One visible primary action per stage.
- No copied entity IDs.
- No manual YAML editing for normal buyers.
- Wi-Fi is asked by the browser immediately after flashing.
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
https://www.passion-wave.com/firmware/rotaryknob/s3/manifest.json
https://www.passion-wave.com/firmware/rotaryknob/esp32/manifest.json
```

Each image must be built from a public factory configuration with:

- no private Wi-Fi credentials;
- no private API encryption key;
- no private OTA password;
- no private MQTT credentials;
- `name_add_mac_suffix` enabled;
- `improv_serial` enabled;
- `captive_portal` enabled;
- `dashboard_import` enabled for ESPHome adoption.

Development builds with private `secrets.yaml` values must never be published
as website installer assets.

## Current Implementation Status

- The website contains `/install/` with an ESP Web Tools install button.
- The website contains `/firmware/rotaryknob/manifest.json`.
- The device defaults blueprint contains Home Assistant entity selectors for
  all `media_player` and `light` entities.
- The firmware stores selected media and light targets persistently and shows
  Wi-Fi, Home Assistant and IP status in settings.
- The current manifest models only one processor.
- Neither production factory binary is published.
- Chip verification, plug-reversal guidance, pairing and the no-code Home
  Assistant config flow are not implemented.

The installer therefore remains a development prototype. See
[Customer product architecture](customer-product-architecture.md) for the
release design and acceptance stages.
