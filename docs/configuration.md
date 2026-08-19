# Configuration Model

Installed devices are configured through shared role layers plus a small
physical-device overlay. Runtime integration uses the encrypted ESPHome Native
API; MQTT is not part of the device firmware.

## Release distinction

- Historical rollback reference: single-profile firmware `1.2.0` (not part of
  the V3 source tree).
- Current coordinated dual-processor beta: `3.0.1-beta.4`.
- Public Factory profiles: credential-free first adoption only.
- Private Managed profiles: encrypted API, authenticated OTA and thin
  per-endpoint entrypoints over two shared processor roles. The repository has
  four entrypoints for two device identities; live evidence currently covers
  one physical dual-MCU pair.

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
| Screensaver Startverzögerung | `number` | yes |
| Screensaver Abdunkeldauer | `number` | yes |
| Wach halten | `switch` | yes |
| Display Dimmverzögerung | `number` | yes |
| Display Dimmhelligkeit | `number` | yes |
| Display aus ohne Playback | `number` | yes |
| Display aus bei Playback | `number` | yes |
| Offline demo mode | `switch` | yes |

## PassionWave Integration

V3 configures the media-library path only through the `passion_wave` Config
Flow. Install `custom_components/passion_wave`, restart Home Assistant and add
one integration entry per physical RotaryKnob. The form uses typed selectors
for the Bridge registration entity, Music Assistant instance and Music
Assistant player.

The integration stores its Config Entry ID in the Bridge entity
`PassionWave Integration Entry ID`. This is the only firmware-visible media
configuration value. The Bridge never needs the Music Assistant Config Entry
ID or media-player entity as manually editable strings.

The same PassionWave Config Entry owns the Display/S3, Bridge, Music Assistant
player and four ordered light slots. Open **Configure** on that entry to change
any assignment later. The integration writes entity IDs and current friendly
names to the selected display and follows Home Assistant entity renames.

The customer-facing PassionWave device deliberately exposes only the combined
firmware update, `Systemproblem` and `Supportdiagnose`. Structural assignment of
S3, Bridge, Music Assistant, player, light slots and media filters remains in
the guided **Configure** flow. The former quick selects, individual connection
sensors and integration-version sensor are disabled by default; existing
entries are migrated once without deleting registry history.

`Systemproblem` is the single normal health signal. It turns on when either the
S3 display or Bridge contract becomes unavailable and retains both connection
results as attributes. `Supportdiagnose` enables the detailed diagnostic path
on both processors together. Keep it off during normal operation and use it
only while collecting evidence for a fault. Native ESPHome transport and
configuration entities remain enabled where the runtime contract needs them,
but are hidden from customer dashboards.

Runtime delivery is event-driven: media and light changes are forwarded
immediately. Independently of events, Home Assistant sends the current runtime
and target snapshot every 15 minutes; Bridge and S3 also republish their
authoritative snapshots on the same cadence. This bounded fallback heals a
missed event without restoring high-frequency polling.

## Offline / Promo Demo Mode

When the device boots without a Wi-Fi connection, it enters a local demo mode
after a short timeout. This mode is intended for product demos away from the
customer's Home Assistant installation.

Demo mode provides local default values for:

- weather location, temperature, forecast and rain status;
- media source, playlists, radios, podcasts and demo tracks;
- four light slots, brightness values and local rotary/touch behavior.

While demo mode is active, Home Assistant service calls, weather
fetches and network image downloads are skipped. This prevents long retries or
empty states when the device is used only as a portable demo unit. When Wi-Fi
connects, the firmware disables demo mode, clears the demo caches and returns to
the normal Bridge/Native-API path.

The Settings page contains a `Demo` entry and Home Assistant exposes
`scrollwheel Demo` as a persistent configuration switch. When it is off, the
offline promo demo will not start. When it is on, the device can start the demo
only while Wi-Fi is missing; with Wi-Fi connected the demo remains inactive.

## Display Protection

Below 100% battery state, the display follows a two-stage idle policy. It dims
after `Display Dimmverzögerung` (default 15 seconds) to `Display
Dimmhelligkeit` (default 10%). Without active playback it switches off after
`Display aus ohne Playback` (default 60 seconds); while the selected media
player reports `playing`, it switches off after `Display aus bei Playback`
(default 180 seconds). The timeout always measures from the last touch or
rotary input. Timer and alarm activity prevent automatic display shutdown.

The Settings page exposes the persistent developer switch `DEV: Wach halten`;
Home Assistant exposes the same setting as `Wach halten`. While enabled, it
blocks automatic screensaver entry, dimming, display shutdown and deep sleep.
It is disabled by default and should remain disabled in normal battery use.

At 100% on external power, the existing protection behavior remains unchanged:
after 15 minutes without activity the backlight dims to 18% but LVGL stays
active. Any touch or rotary step restores the normal 70% UI brightness.

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

The Bridge calls `passion_wave.get_library`; the integration delegates to the
selected Music Assistant instance and normalizes playlist, radio and podcast
pages. It calls `passion_wave.get_playlist_tracks` for playlist contents; Home
Assistant expands `browse_media`, slices the result and returns at most 64
normalized rows.

The PassionWave Options Flow provides searchable multiple-selection fields for
visible playlists, radios and podcasts. `Alle automatisch` is the default and
follows the complete Music Assistant library. Remove that value to show only
selected entries. An empty selection hides the corresponding category.
The initial setup does not interrupt onboarding with this optional filter:
after Bridge, Music Assistant instance and player are selected, the Config
Entry is created with all three categories set to `Alle automatisch`.

Only stable Music Assistant URIs are stored as a visibility filter. Names,
ordering and playlist contents still come from Music Assistant. Add, remove,
rename or favorite media there; PassionWave does not maintain a second media
database. Up to 500 entries per category are offered by the configuration
dialog. The display requests another page when only five rows remain, hiding
the API/UART round trip during normal scrolling.

## Manual Configuration

Manual Music Assistant IDs and raw playlist JSON are unsupported in V3.
Reconfigure the PassionWave Config Entry in **Settings > Devices & services**
instead. Light labels should remain short enough for the 360 × 360 display.

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
