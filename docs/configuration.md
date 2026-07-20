# Configuration Model

The device is configured in two layers.

## Device Runtime Settings

These settings are available directly on the ESPHome device in Home Assistant.
They are stored persistently on the ESPHome device.

| Setting | Home Assistant entity type | Stored on device |
| --- | --- | --- |
| Media entity ID | `text` | yes |
| Media label | `text` | yes |
| Media runtime state | `text` | no |
| Media runtime title | `text` | no |
| Media runtime artist | `text` | no |
| Media runtime cover URL | `text` | no |
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
| Offline demo mode | `switch` | yes |

## Dynamic Home Assistant Selection

ESPHome template text entities cannot show a dynamic Home Assistant entity
dropdown by themselves. The firmware therefore stores raw entity IDs, while the
recommended Home Assistant blueprint provides the comfortable entity picker.

The blueprint selects from:

- all Home Assistant `media_player` entities for the media target; choose a
  Music Assistant capable player for playlist/radio/podcast playback.
- all Home Assistant `light` entities for light slots 1 to 4.

When the blueprint runs, it writes the selected entity IDs and their friendly
names into the ESPHome text entities with `text.set_value`. The Rotaryknob then
uses those values for `media_player.*` and `light.*` service calls.

For media targets, the blueprint also relays the selected player's runtime
state, title, artist and cover URL into diagnostic Text entities. That relay is
what makes Play/Pause state, cover display and the media cover screensaver work
for arbitrary selected `media_player` entities.

Without the blueprint, the firmware still supports arbitrary runtime media
targets. If `Rotaryknob Media Entity ID` contains a real `media_player.*` entity,
the device polls Home Assistant with `homeassistant.action` and a
`response_template`. Home Assistant renders the selected player's state,
friendly name, title, artist, cover URL, volume, progress, shuffle and repeat
attributes into a JSON response. The ESPHome UI then uses that response for the
Play/Pause icon, cover image and media cover screensaver. No extra Home
Assistant automation is required.

If the media entity text is empty or still contains the public placeholder
`media_player.passion_wave_media`, the firmware falls back to the compile-time
`ha_player` and subscribes directly to that static player's attributes.

## Offline / Promo Demo Mode

When the device boots without a Wi-Fi connection, it enters a local demo mode
after a short timeout. This mode is intended for product demos away from the
customer's Home Assistant installation.

Demo mode provides local default values for:

- weather location, temperature, forecast and rain status;
- media source, playlists, radios, podcasts and demo tracks;
- four light slots, brightness values and local rotary/touch behavior.

While demo mode is active, Home Assistant service calls, MQTT requests, weather
fetches and network image downloads are skipped. This prevents long retries or
empty states when the device is used only as a portable demo unit. When Wi-Fi
connects, the firmware disables demo mode, clears the demo caches and returns to
the normal Home Assistant/MQTT path.

The Settings page contains a `Demo` entry and Home Assistant exposes
`scrollwheel Demo` as a persistent configuration switch. When it is off, the
offline promo demo will not start. When it is on, the device can start the demo
only while Wi-Fi is missing; with Wi-Fi connected the demo remains inactive.

## Display Protection

On battery, the display can enter the existing full sleep path and LVGL is
paused. On external power, the device does not fully sleep; after 15 minutes
without touch or rotary activity it dims the backlight to a low protection
level. The UI stays alive, and the next touch or rotary step restores normal
brightness.

## Weather Source

The weather page uses the compile-time secret `ha_weather_entity`. Set it to an
existing Home Assistant weather entity, for example `weather.forecast_home` or a
local provider such as a DWD entity. If this entity does not exist, current
temperature and forecasts cannot match Home Assistant because ESPHome receives
no state or `weather.get_forecasts` response for the configured source.

`weather_location_fallback` is only used until the weather entity's
`friendly_name` is received from Home Assistant.

## Raw Light mV Calibration

The optional package
`home_assistant/packages/light_mv_calibration.yaml` converts a raw
millivolt-like brightness sensor into an estimated lux value and a coarse
daylight class. It is intended for sensors such as
`sensor.outdoor_regenlichtsensor_illuminance_raw`, where the vendor exposes an
undocumented raw light channel instead of calibrated illuminance.

The conversion is deliberately local and calibration-based. There is no
universal mV-to-lux table for arbitrary light sensors because the voltage
depends on the sensor electronics, lens, orientation, dirt and mounting
position. Configure the source entity in `input_text.light_mv_source_entity`,
then adjust the dark, dim, overcast-daylight and direct-sun mV anchors. The
package can slowly recalibrate the dark, overcast and sun anchors from recent
history, sun elevation and weather condition, but the result remains an
estimate unless validated with a reference lux meter.

## Media Library Lists

The selected `media_player` controls playback and provides runtime status. It
does not automatically provide playlist, radio or podcast rows for the
Rotaryknob popup. Those rows are read from MQTT:

| Content | Topic |
| --- | --- |
| Static playlist list | `passion_wave/media/playlists` |
| Paged playlist response | `passion_wave/media/playlists/state` |
| Radio list | `passion_wave/media/radios` |
| Podcast list | `passion_wave/media/podcasts` |
| Playlist-track request | `passion_wave/media/playlist_tracks/request` |
| Playlist-track response | `passion_wave/media/playlist_tracks/state` |

For Music Assistant, publish retained JSON arrays with objects containing
`name`, `uri` and `media_type`. The firmware also sends playlist page requests
to `passion_wave/media/playlists/request`; a Home Assistant automation can use
`music_assistant.get_library` and answer with `items`, `offset`, `next_offset`,
`has_more` and the original `request_id`.

The included blueprint
`home_assistant/blueprints/automation/passion_wave/rotaryknob_music_assistant_library.yaml`
implements this bridge. Create one automation from it and select the Music
Assistant config entry. Keep retained bootstrap lists compact; larger lists are
loaded through the request topics so the ESPHome UI does not need to ingest very
large MQTT payloads at boot.

## Manual Configuration

Without the blueprint, open the ESPHome device in Home Assistant and edit the
text entities manually:

```text
Rotaryknob Media Entity ID: media_player.your_player
Rotaryknob Media Label: Media
Rotaryknob Light Slot 1 Entity ID: light.your_light
Rotaryknob Light Slot 1 Label: Main
```

Keep labels short enough for the 360 x 360 display.

Manual raw media entity configuration can control playback and receive dynamic
status and cover updates. Set `Rotaryknob Media Entity ID` to the desired
`media_player.*`. The firmware reads the dynamic state through
`homeassistant.action`/`response_template`; the blueprint only makes selection
easier by showing Home Assistant entity pickers.

## Privacy Defaults

The public firmware ships only generic placeholders such as
`media_player.passion_wave_media` and `light.passion_wave_light_1`. Real room
names, person names, local hostnames, Home Assistant URLs and secrets belong in
the user's private `secrets.yaml` or in Home Assistant entity selections, not in
this public repository.

## UI Notes

The current public UI uses enlarged navigation hitboxes, clearer light-page
toggle targets, a bottom-to-top temperature scale, explicit day-part markers on
the weather arc and a settings status row for Wi-Fi, Home Assistant and IP
address.

On the settings page, `System` is offset to the right of the back button and
the Home Assistant status label is wide enough for the full text.

## Compile-Time Fallbacks

`esphome/scrollwheel_dynamic_targets.h` still contains generic fallback arrays
for older UI paths and recovery scenarios. They are intentionally anonymized and
should not be edited with private names before publishing a fork.
