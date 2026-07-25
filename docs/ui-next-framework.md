# UI Next Framework

UI Next implements the five-view circular interface proposed for the Passion
Wave Rotaryknob. It is enabled only in the dedicated S3 test profile through
the `ui_next_enabled` substitution. The production profile defaults to false.

## Runtime architecture

[`ui_next_framework.h`](../esphome/ui_next_framework.h) creates one persistent
LVGL object tree on `lv_layer_top()`. This global layer remains above ESPHome's
separate legacy page screens. Widgets are allocated once and never rebuilt
during normal navigation.

```text
root (transparent, persistent)
├── Weather view (temperature segments + compact condition/metric group)
├── Light view
├── Media view (volume arc + linear progress + picker/options actions)
├── Time view (timer + alarm)
├── More view (four utility launchers)
├── shared status line
└── five-button curved navigation rail
```

Only one primary view is visible. Navigation changes hidden flags and styles;
it does not destroy objects or load images. The utility launchers temporarily
hide the black primary panel while retaining the right rail over the complete
legacy 1.2.0 page. The media picker is the deliberate exception: because it is
a modal selection surface, the rail is hidden while the picker is open and is
restored on close or selection. Selecting a primary rail item returns
immediately to UI Next.

Revision `.87` reserves the complete media content width for title and artist.
Artwork remains available in the automatic full-screen cover view, but no
miniature tile competes with long metadata on the primary control surface.

Revision `.98` gives the media picker a 60 x 48 pixel Home hitbox at the upper
right. The icon remains visually compact, but the target extends inward and is
no longer trapped in the hard-to-reach curved edge of the round display.

The legacy-background audit leaves only deliberate specialty screens:
full-screen media artwork, screensaver, radar, photos, house, settings, timer,
alarm and the non-WLED light detail editor. Their entry paths call
`show_legacy()` explicitly, which hides every UI Next view and the main rail.
Their return paths restore the matching UI Next view. The inherited Weather,
Media and general Light pages are not valid backgrounds for UI Next. The media
picker is reparented to the global top layer and therefore opens over the new
Media view rather than over the inherited Media page.

## Colour system

The UI uses a housing-aware `Smoked Aqua` palette selected for the saturated
raspberry/rose metal enclosure. Warm neutral white (`#F2F1EE`) and cool greys
carry all information; the desaturated aqua (`#68B8BA`) appears only on active
controls, selection markers and progress. This complementary relationship keeps
the screen distinct from the enclosure without the neon character of bright
cyan. Panels use `#111519`, tracks `#292F33`, secondary text `#899297`, inactive
navigation `#596268`, and the display base remains near-black `#07090B`.

The media picker follows the same system as a compact floating sheet rather
than a second full-screen design. Its `#111519` surface has a soft 38 px radius
and a single subtle `#292F33` edge. Tabs and rows stay neutral until selected;
selection uses `#68B8BA` with near-black text. Narrow 34 px tabs and unbordered
40 px rows keep the picker quiet and preserve useful space on the round panel.
Although its reusable widget definitions still originate in the 1.2.0 YAML,
the popup is reparented to `lv_layer_top()` when first opened. The framework
keeps the UI Next media view active underneath it; loading the old media page
is neither required nor permitted by this action path.

## Five primary destinations

| View | Main interaction | Existing function source |
| --- | --- | --- |
| Wetter | temperature arc, condition/wind symbols, humidity, hourly context plus two daily summaries | weather globals and radar page |
| Licht | selected light, brightness, on/off, source picker, WLED presets | four dynamic light slots |
| Medien | title, artist, progress, transport, volume, options | media cache and HA media actions |
| Zeit | timer start/reset and alarm toggle | existing timer/alarm state machines |
| Mehr | radar, photos, house and settings | complete legacy utility pages |

The rail therefore exposes exactly five stable concepts while every 1.2.0
function remains reachable. On the Light view, tapping the large percentage
toggles the selected light. Tapping its name opens a pre-allocated selector
for all four configured light slots. The top-left `LICHT` caption is omitted as
the selected rail entry already supplies that context. `Detail` opens a WLED
preset selector when the selected entity is a WLED light. The classic ESP32
subscribes to the Home Assistant select, transfers up to nine dynamic preset
names plus the active selection, and executes validated selections. If no
preset options are configured, the modal states that explicitly instead of
presenting invented choices. Non-WLED lights retain the complete legacy detail
editor.

With bridge `.13`, paginated playlist and track response JSON is no longer
parsed on the display processor while the proxy is healthy. UI Next receives a
complete bounded cache plus paging metadata and swaps it only after the UART
CRC gate succeeds. Picker geometry and interaction remain unchanged.

Revision `.43` routes EC1 rotation to the open media picker on both the legacy
media page and UI Next page 22. Rotation changes only the selected row, keeps
the highlighted row visible and may request the next bounded page near the
list end; it cannot change volume or the primary navigation while the picker
is open.

Revision `.44` makes the legacy media picker a true modal input surface for UI
Next. Hidden rail hit-testing is disabled on touch-down, the release fallback
is suppressed for 350 ms after a selection, and the same gesture therefore
cannot navigate to or activate the Light view underneath. Playlist selection
arms a one-shot start of track zero after the initial track page has arrived;
radio and podcast selection clear that one-shot state.

Revision `.45` completes the media-selection transport. Playlist-track, radio
and podcast selections are sent as compact library kind/index commands over the
inter-MCU link. The ESP32 resolves the cached URI and invokes
the configured network-side action; the S3 no longer depends on its legacy
direct Home Assistant service path. A result frame reports accepted selections
back to the S3 diagnostics. Bridge `.15` uses the native
`music_assistant.play_media` action, and `.17` additionally owns both outbound
MQTT page requests.

Bridge revision `.15` uses the native `music_assistant.play_media` action with
the cached URI as `media_id`. A success result is no longer emitted when the
request is merely queued; `code=0` now means Home Assistant acknowledged the
action, while `code=5` carries an action error into the ESP32 diagnostics.

The weather primary surface aligns the current-condition symbol with the lower
edge of the large temperature. Below it, the translated condition is the
primary line and the calculated apparent temperature is a smaller muted second
line, for example `Sonnig` / `Gefühlt 24°`. Apparent temperature is recalculated
from temperature, humidity and wind, so the dual-MCU bridge requires no
additional Home Assistant helper. Humidity and wind share one compact line:
small monochrome symbol followed by its numeric value, separated by a fine
neutral divider and without panels or repeated captions. The wind field
reserves enough width for the complete `km/h` unit and three-digit values
without touching the navigation rail. Tapping the large
temperature opens a pre-allocated daily context with current conditions plus
Morning, Midday, Evening and Night rows. Each row receives its nearest hourly
condition and temperature. Radar is available inside this context; the main
weather surface contains no duplicate radar button or central Min/Max line.
Forecast conditions are deliberately not collapsed into one generic cloud:
`cloudy`, `partlycloudy`, `fog` and `windy` use separate monochrome symbols.
Rain, storm, snow, sun and clear night retain their dedicated symbols. An
unsupported Home Assistant condition is rendered as a question-mark symbol
instead of silently appearing as partly cloudy; the ESP32 bridge also logs the
raw condition and affected daily index.

## Encoder behavior

The hardware-PCNT reader remains unchanged. UI Next maps its signed batches by
view:

- Light: brightness in five-percent increments;
- Media: volume in two-percent increments;
- Time: timer duration in minute increments;
- Weather and More: no accidental value changes.

The five right-hand main-menu entries are touch-only. Encoder input never
changes the active top-level view. A rotary batch on Weather or More is simply
discarded, preventing it from becoming a brightness or volume change after an
unwanted page transition.

Touch selects navigation and discrete actions. Touch event callbacks only put a
small enum into a one-slot action queue. The 10 ms application interval drains
that queue and executes existing ESPHome scripts or Home Assistant actions.
No network request, allocation or YAML automation executes inside an LVGL event
callback.

Primary rail navigation is committed on touch-down instead of waiting for the
CST816 release timeout. Only the previous and next view plus their two rail
buttons are invalidated. Discrete buttons continue to use release events so
swipes cannot trigger them accidentally.

Each right-rail touch target still extends beyond the physical edge, but its
surface remains black and invisible. A narrow cyan marker at x=356 identifies
the selected destination, except on Media and Time where the round display edge
makes it resemble an unrelated vertical separator. Those two views therefore
use only their cyan icon and neutral-white name as the active state. In every row,
inactive entries use a darker neutral. Icon and title use
separate fixed-size label boxes aligned with `LEFT_MID` on the same centerline,
so differing icon and text font metrics cannot shift individual entries
vertically.

The CST816 release handler additionally applies the same fixed hit boxes as a
fallback. This prevents a page-layer update from swallowing the LVGL click. A
180 ms de-duplication window ensures that the LVGL and coordinate paths can
never execute the same action twice. Rotating on Light, Media or Time changes
the value shown there; rotating on Weather or More is ignored.

When UI Next is enabled, the inherited 800 ms boot action refreshes weather data
but does not load the legacy weather page. If another inherited automation loads
a legacy screen unexpectedly, UI Next remains visible because its root belongs
to LVGL's global top layer instead of that screen. The framework synchronizes the
page number and reorders its root only once; it never reorders periodically while
a touch is in progress.

## Arc design

Media and Weather each use one pre-created, uninterrupted 132-degree LVGL arc.
Its restrained 7-pixel width forms a continuous premium bezel without any
segment boundaries. The neutral track and cyan indicator are two parts of the
same object; updates only change its cached 0–100 value and indicator opacity.
Both arcs share the same 348-pixel geometry along the left bezel.

- Volume uses cyan active segments and a charcoal track. Its compact percentage
  continues just beyond the lower arc endpoint with the same tangential
  geometry as the weather minimum.
- Temperature uses the same restrained cyan as all other active/progress states;
  condition and metric symbols remain neutral.
- Temperature segments use the valid daily minimum and maximum as their scale.
  Tiny numeric values continue just beyond the upper and lower arc endpoints
  on the circular path. Their slight tangential rotation keeps them visually
  aligned with the arc without extra `MAX`/`MIN` captions. Missing, reversed,
  implausible or less than 1 °C-wide daily
  bounds automatically fall back to -10 through +40 °C.
  At or below the lower bound the first segment remains active, so the visual
  temperature indicator never vanishes completely.
- Song position uses a thin linear bar below the artist. Elapsed and total time
  are rendered beside it; the bezel remains reserved for volume.
- The complete media content column is inset from the left volume arc. Its
  title uses LVGL circular scrolling only when the rendered text exceeds the
  fixed clipped window; short titles remain stationary.
- Updates change only the arc value and indicator opacity; arcs are never
  recreated.

## Media context

Two equal 48-pixel icon buttons share one baseline below the transport controls.
The library icon opens the complete Media Picker for lists, playlists, radio
and podcasts. The three-dot icon toggles the small pre-allocated modal panel
for Shuffle and Repeat One. Text captions are deliberately omitted on the
primary surface. Closing the options context or navigating to another primary
view only changes its hidden flag; no widget is created at runtime.

The shared clock is horizontally centered on the physical display and uses the
precompiled Poiret One clock face. Battery percentage is a separate, smaller
numeric label directly below it without an `AKKU` caption. Humidity is
restricted to the weather content and no longer
occupies this global status area.

## Update policy

- input and queued actions: 10 ms;
- visible state reconciliation: 100 ms;
- LVGL display update: 33 ms;
- label text changes are skipped when content is identical;
- arc colors and state-dependent button styles are skipped while their cached
  visual state is unchanged;
- primary navigation changes only hidden flags and active-menu styles;
- legacy pages refresh only while explicitly opened;
- the existing weather screensaver suspends the complete UI Next root and
  restores it after exit.

The framework uses fixed object arrays, bounded action storage and existing
compiled fonts/icons. It performs no JSON parsing, image scaling, blur, shadow
or large opacity animation.

The proposed photographic weather collage is retained as a source reference in
[`assets/screensaver/`](../assets/screensaver/README.md). Its coverage audit
shows that it cannot yet replace the generated screensaver: clear night, hail,
mixed snow/rain and both wind variants need dedicated motifs. The 1254-pixel
collage must not be compiled directly; approved motifs require offline crop,
resize and conversion first.

## Regenradar

The full-screen radar follows the same dark, restrained visual language as UI
Next. A precomposed map fills the 320×320 content square. The upper translucent
capsule shows `Regen jetzt`, `Regen in n min` or `Kein Regen erwartet`; its
second line shows the measured source direction and speed when Rain Warner can
derive a stable motion vector. The lower capsule contains 264/132/66 km zoom
controls and a compact source attribution.

Map composition, radar alpha blending, geographic cropping and JPEG encoding
run in Home Assistant every five minutes. The S3 therefore performs no map
projection or runtime resampling. On the radar page, clockwise/counterclockwise
encoder movement changes only the zoom level. The previous decoded frame stays
visible until the replacement has passed transfer CRC and JPEG decoding.

## Activation

The stable base contains:

```yaml
substitutions:
  ui_next_enabled: "false"
```

The test S3 overrides it:

```yaml
substitutions:
  ui_next_enabled: "true"
```

This makes UI Next testable without changing the online production device.

## Acceptance checklist

- five rail items are visible and remain within the round display;
- active rail item and view always match;
- Media has a left volume arc plus a visible linear song-progress bar;
- elapsed and total media time follow position and duration from the ESP32;
- Shuffle and Repeat One are reachable through the media options context;
- time and battery percentage remain visible in the centered status line;
- Weather has the matching left temperature arc;
- Weather shows permanently labelled humidity and wind values below the temperature range;
- rotary brightness, volume and timer changes remain loss-free;
- media previous/play/next still reach Home Assistant;
- light toggle, timer, alarm, radar, photos, house and settings work;
- screensaver, dimming, sleep and wake behavior remain intact;
- EC1 read errors and both UART protocol-error counters remain zero.
