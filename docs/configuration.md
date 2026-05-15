# Configuration Model

The device is configured in two layers.

## Device Runtime Settings

These settings are available directly on the ESPHome device in Home Assistant.
They are stored persistently on the ESPHome device.

| Setting | Home Assistant entity type | Stored on device |
| --- | --- | --- |
| Media entity ID | `text` | yes |
| Media label | `text` | yes |
| Light slot 1 entity ID | `text` | yes |
| Light slot 1 label | `text` | yes |
| Light slot 2 entity ID | `text` | yes |
| Light slot 2 label | `text` | yes |
| Light slot 3 entity ID | `text` | yes |
| Light slot 3 label | `text` | yes |
| Light slot 4 entity ID | `text` | yes |
| Light slot 4 label | `text` | yes |
| Vibration | `switch` | yes |
| Rotary effect | `number` | yes |
| Timer done effect | `number` | yes |
| Screensaver timeout | `number` | yes |

## Dynamic Home Assistant Selection

ESPHome template text entities cannot show a dynamic Home Assistant entity
dropdown by themselves. The firmware therefore stores raw entity IDs, while the
optional Home Assistant blueprint provides the comfortable entity picker.

The blueprint selects from:

- all `media_player` entities for the media target; choose a Music Assistant
  capable player for playlist/radio/podcast playback.
- all `light` entities for light slots 1 to 4.

When the blueprint runs, it writes the selected entity IDs and their friendly
names into the ESPHome text entities with `text.set_value`. The Rotaryknob then
uses those values for `media_player.*` and `light.*` service calls.

## Manual Configuration

Without the blueprint, open the ESPHome device in Home Assistant and edit the
text entities manually:

```text
Rotaryknob Media Entity ID: media_player.your_player
Rotaryknob Media Label: Living Room
Rotaryknob Light Slot 1 Entity ID: light.your_light
Rotaryknob Light Slot 1 Label: Main
```

Keep labels short enough for the 360 x 360 display.

## Privacy Defaults

The public firmware ships only generic placeholders such as
`media_player.passion_wave_media` and `light.passion_wave_light_1`. Real room
names, person names, local hostnames, Home Assistant URLs and secrets belong in
the user's private `secrets.yaml` or in Home Assistant entity selections, not in
this public repository.

## Compile-Time Fallbacks

`esphome/scrollwheel_dynamic_targets.h` still contains generic fallback arrays
for older UI paths and recovery scenarios. They are intentionally anonymized and
should not be edited with private names before publishing a fork.
