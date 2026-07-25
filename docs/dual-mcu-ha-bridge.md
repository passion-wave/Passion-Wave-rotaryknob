# Dual-MCU Home Assistant Bridge

Revision `1.2.0-ui-next.98` / `1.2.0-ha-bridge.50` is the current test
workload split between both processors. The S3 still owns deterministic input
and rendering. The classic ESP32 now owns migrated Home Assistant service calls
and mirrors bounded media/light state records to the S3.

## Runtime data flow

```text
Home Assistant API
       │
       ▼
classic ESP32
  state cache + HA actions
       │ 2 Mbit/s COBS + CRC-16
       ▼
ESP32-S3
  EC1 + UI Next + local optimistic state
```

The bridge transports:

- API readiness, an immediate reconnect snapshot and a 60-second periodic
  loss-recovery snapshot;
- media state, volume, position, duration, shuffle, repeat, title and artist;
- on/off and brightness for four light slots;
- previous, play/pause, next, volume, shuffle and repeat actions;
- light on, off and brightness actions.
- dynamic WLED preset names, active preset and validated preset-selection actions;
- current weather temperature, humidity, wind, condition and location;
- five daily ranges/conditions, four hourly slots and the rain hint.

All records are fixed or bounded to the protocol's 192-byte payload. Title and
artist are truncated in transport rather than allocating a large frame. No JSON
crosses the processor link.

`BRIDGE_STATUS` advertises the extended-media capability independently from
API readiness. An updated S3 therefore remains compatible with bridge `.1`:
basic media/light offload stays active, while progress, shuffle and repeat keep
using the direct S3 fallback until bridge `.2` is online.

Bridge `.5` additionally performs both `weather.get_forecasts` calls. It parses
the Home Assistant JSON response on the classic ESP32 and sends one fixed
42-byte record to the S3; JSON never enters the display processor's UART path.
The record contains five daily forecasts, four representative hours and the
rain ETA/probability. The S3 considers forecast offload ready only after at
least tomorrow, the following day and all four hourly slots are valid. Its
original daily/hourly actions remain compiled and resume automatically when a
complete bridge record has not arrived for 20 minutes. Radar image download
remains available as the fallback path.

Bridge `.10` adds the first bulk-data migration. The classic ESP32 downloads the
radar JPEG in a dedicated FreeRTOS task and streams it to the S3 in acknowledged
data chunks. Protocol version 3 raises the bounded frame payload to 192 bytes,
leaving 186 bytes per image chunk while keeping the encoded UART frame below
the one-byte COBS boundary. It sends at most one radar chunk every 4 ms after
encoder, action and state processing. A 64-frame receiver queue
absorbs short LVGL stalls without dropping image chunks. Per-frame
CRC-16, contiguous offsets, total length and an end-to-end CRC-32 protect the
image. Every begin, data and end frame is acknowledged; a missing or damaged
frame is retransmitted after 40 ms. The S3 reuses the existing runtime JPEG decoder, so the radar widget and
320 x 320 display buffer are unchanged. A 12 second transfer timeout, invalid
offset, CRC mismatch, HTTP error or decode error activates the original direct
S3 download for that request.

Revision `.50` / UI `.97` completes the responsive asset path. Retry cooldowns
are isolated by asset kind, so a missing photo, cover or floorplan cannot delay
radar. Radar requests take priority over queued decorative assets. The bridge
prefetches radar once after link readiness, while the S3 retains the last valid
image in one buffer and decodes the new JPEG into the inactive buffer. Only a
successful decode swaps the visible buffer. Opening Radar therefore paints the
cached image immediately. A cache younger than 60 seconds requires no network
or decoder work; an older frame refreshes in the background. Explicit reloads
bypass both the freshness window and the passive five-second request throttle.
Three successive final test reloads
completed in 0.68–0.75 seconds each with zero protocol errors, zero queue
overflows and a maximum measured steady-state S3 scheduler gap of 4 ms. An independent
12.5-second transaction watchdog requeues a request if a bridge capability
transition resets its inner client before the first data frame arrives. The
ESP32 server independently aborts an unacknowledged transfer after 12 seconds,
so an S3 restart cannot leave the proxy permanently busy.

The bridge publishes the raw five-day condition sequence as
`ESP32 Daily Forecast Conditions`; the S3 publishes the decoded sequence as
`S3 Forecast Conditions Received`. These diagnostics distinguish genuinely
identical forecasts from icon mapping or transport defects.

Bridge `.11` subscribes to the retained Music Assistant playlist, radio and
podcast bootstrap topics on the classic ESP32. JSON is parsed there into at
most 192 bounded entries per list. The retained playlist payload is only a
fast bootstrap prefix; it is never treated as the complete catalog. The S3
requests one list at a time and
receives versioned binary records through the same acknowledged 42-byte chunk
transport with contiguous offsets and end-to-end CRC-32. Only after a complete
list has decoded successfully does the S3 suppress that list's original MQTT
callback. A changed retained payload invalidates only its own feature bit and
triggers a fresh transfer. Link loss clears all three bits and restores the
original S3 MQTT route.

Paginated playlist and playlist-track requests still originate on the S3 in
this compatibility stage. Their JSON responses are parsed on the ESP32 from
bridge `.13` onward.

Bridge `.12` subscribes to the configured WLED preset select on the classic
ESP32. Home Assistant's `options` attribute is parsed into at most nine bounded
names. Each update is sent as generation-tagged item frames followed by one
commit record; the S3 rejects incomplete generations and retains its last
complete list. Selecting a row sends only its index and the configured select
entity to the ESP32. The ESP32 verifies both before resolving the option name
and calling `select.select_option`. If the bridge is unavailable, the S3 can
use its last complete list through the retained direct Home Assistant action.
An empty Home Assistant option list is represented explicitly and does not
create synthetic presets.

Bridge `.13` owns JSON parsing for paginated playlist and playlist-track
responses. It accepts only request IDs belonging to the test S3 and sends
bounded delta pages containing offset, next offset and `has_more`. The S3
accumulates display names only after each page passes contiguous-transfer and
CRC-32 validation. The classic ESP32 keeps only a compact global URI/item-ID
index for playback and further track requests. This avoids the former
cumulative name/blob duplication and its heap peak on large catalogs. A proxy
timeout re-enables the original S3 response parser for ten seconds.

Bridge `.14` adds index-based media selection. The S3 sends only the library
kind and selected index; the ESP32 resolves both against its canonical cache.
Bridge `.15` calls the native `music_assistant.play_media` action with the
resolved URI and reports success only after Home Assistant acknowledges the
action. Bridge `.16` targets the native Music Assistant player
`media_player.roam_2`. Its former target `media_player.unnamed_room` is the
generic Sonos entity: transport controls work there, but Music Assistant
library selection does not address the MA queue. Both entities have the same
physical `RINCON_C43875C917BC01400` identifier in this Home Assistant registry.
The S3 keeps a valid Home Assistant-selected runtime target across reboots.
Only an empty value or the public factory placeholder is replaced by the
compiled fallback. The former unconditional boot assignment could silently
restore an old player and make optimistic volume feedback jump to that
player's value.

The fast bridge path still requires the compiled S3 and ESP32 targets to match
the persisted S3 targets. Private test wrappers therefore override the same
native Music Assistant entity and the same four light entities in both
profiles. The current Sonos Move test installation uses
`media_player.move_2`; the generic Sonos entity can provide transport and
volume but is not the correct target for Music Assistant queue replacement.

Bridge `.17` moves the two remaining outbound library page requests. S3 `.47`
sends a fixed six-byte command containing list kind, offset, limit and selected
playlist index. The ESP32 resolves that index against its canonical cache,
constructs the existing request JSON and publishes it to MQTT. An immediate
result record distinguishes accepted MQTT publishes from invalid indices or a
disconnected broker. A rejected request opens the original S3 MQTT fallback
for ten seconds; successful responses continue through the existing bounded
binary list transfer.

Bridge `.38` makes playlist playback an atomic queue replacement. Playlist
selection resolves the canonical playlist URI on the ESP32 and calls
`music_assistant.play_media` with `enqueue: replace`. The separately fetched
track page remains a browser view only. It no longer autoplays its first track,
which previously left an unrelated Music Assistant queue behind the selected
first item. S3 `.78` identifies this route explicitly as
`PLAYLIST_PAGE`; bridge `.38` accepts both playlist kind identifiers for
backward compatibility.

The current live acceptance automatically transferred all 140 Music Assistant
playlists, including every entry after the 40-item retained bootstrap. Both
processors reported 140 cached playlist locators and zero protocol errors.
Playlist tracks use the same delta-page scheme and are prefetched in bounded
chunks while the ESP32 retains their compact global URI index.

S3 `.56` turns that proven path into a hard normal-operation boundary. The S3
ignores retained playlist, radio, podcast and track JSON while the bridge owns
the library, and it no longer falls through to direct MQTT merely because the
ESP32 cache is still starting. Only an explicit library error or a bridge loss
lasting more than 12 seconds enables the compiled compatibility parser and
direct selector. Thirty stable seconds restore exclusive ESP32 ownership.

## Compatibility and fallback

The S3 activates the bridge only when all conditions are true:

1. UART heartbeat is fresh;
2. the ESP32 reports an active native Home Assistant API connection;
3. the configured media target and all four light targets match the compiled
   ESP32 subscriptions;
4. bridge status remains fresher than 1.6 seconds.

If any condition fails, `dual_mcu_ha_bridge_ready` becomes false immediately.
Existing S3 Home Assistant services remain compiled and resume as the action
fallback. Dynamic target changes therefore never send an action to the wrong
entity.

The S3's direct Home Assistant state components remain present during this
compatibility revision, but their media/light callbacks yield while the bridge
is ready. The media-library MQTT callbacks now also yield unless the explicit
library fallback is active. Removing the remaining state subscriptions, and
later normal S3 Wi-Fi, requires a separate regression gate.

## Protocol evolution through version 3

| Message | Direction | Purpose |
| --- | --- | --- |
| `BRIDGE_STATUS` | ESP32 → S3 | API readiness |
| `SNAPSHOT_REQUEST` | S3 → ESP32 | reconnect/state recovery |
| `MEDIA_STATE` | ESP32 → S3 | state, volume, flags, position and duration |
| `MEDIA_TEXT` | ESP32 → S3 | bounded title or artist |
| `LIGHT_STATE` | ESP32 → S3 | slot, on/off and brightness |
| `HA_ACTION` | S3 → ESP32 | bounded action and dynamic entity ID |
| `VOLUME_SET` | S3 → ESP32 | sequence plus latest requested percentage |
| `VOLUME_BRIDGE_ACK` | ESP32 → S3 | immediate UART receipt timestamp |
| `VOLUME_RESULT` | ESP32 → S3 | correlated HA-confirmed result |
| `WEATHER_STATE` | ESP32 → S3 | fixed-point temperature, humidity and wind |
| `WEATHER_TEXT` | ESP32 → S3 | bounded condition or location text |
| `WEATHER_FORECAST` | ESP32 → S3 | fixed 42-byte daily/hourly/rain snapshot |
| `RADAR_REQUEST` | S3 → ESP32 | request a radar download |
| `RADAR_BEGIN` | ESP32 → S3 | transfer ID and optional content length |
| `RADAR_CHUNK` | ESP32 → S3 | offset plus up to 42 JPEG bytes |
| `RADAR_END` | ESP32 → S3 | final byte count and end-to-end CRC-32 |
| `RADAR_ERROR` | ESP32 → S3 | bounded error code that activates S3 fallback |
| `RADAR_ACK` | S3 → ESP32 | accepted transfer ID and next byte offset |
| `LIBRARY_REQUEST` | S3 → ESP32 | request bootstrap or paginated library cache |
| `LIBRARY_BEGIN/CHUNK/END` | ESP32 → S3 | bounded list transfer with total and CRC-32 |
| `LIBRARY_ACK` | S3 → ESP32 | accepted transfer ID and next byte offset |
| `LIBRARY_CHANGED/ERROR` | ESP32 → S3 | invalidate one cache or activate fallback |
| `WLED_PRESET_ITEM` | ESP32 → S3 | generation-tagged bounded preset name |
| `WLED_PRESET_META` | ESP32 → S3 | atomically commit count and active preset |
| `MEDIA_LIBRARY_PLAY` | S3 → ESP32 | select a cached media URI by kind/index |
| `MEDIA_LIBRARY_PLAY_RESULT` | ESP32 → S3 | report the acknowledged HA action result |
| `LIBRARY_PAGE_FETCH` | S3 → ESP32 | request playlist/track paging without S3 MQTT |
| `LIBRARY_PAGE_FETCH_RESULT` | ESP32 → S3 | report MQTT acceptance or a bounded error code |

Protocol v2 uses a 64-frame receive queue so a full snapshot and brief LVGL
stalls cannot overflow it. Version mismatches are rejected by the existing
decoder and cannot mutate state.

## Live diagnostics

On the S3:

- `ESP32 Home Assistant Bridge`;
- `ESP32 Coprocessor Link`;
- `Coprocessor Status`;
- `Inter-MCU Protocol Errors`;
- `S3 Forecast Conditions Received`;
- `S3 Radar Proxy Status` and `S3 Radar Proxy Bytes`.
- `S3 Library Proxy Status`.
- `S3 WLED Preset Status`.

On the ESP32:

- `S3 Link Connected`;
- `ESP32 HA Bridge Actions`;
- `ESP32 HA Bridge Last Action`;
- `UART Protocol Errors`;
- `Encoder Queue Overflows`;
- `ESP32 Daily Forecast Conditions`;
- `ESP32 Radar Proxy Status`.
- `ESP32 Library Proxy Status`.
- `ESP32 WLED Preset Status`.

## Manual acceptance test

1. Confirm both connectivity entities are on and both protocol error counters
   remain unchanged.
2. Change the Home Assistant media volume externally; UI Next must converge to
   the same value through the ESP32 snapshot.
3. Use previous, play/pause, next and rotary volume on UI Next. The ESP32 action
   counter must increase once per coalesced action.
4. While a track is playing, compare position and duration with Home Assistant.
   Toggle shuffle and repeat-one in both directions. The S3 UI must converge and
   the ESP32 action counter must increase for controls initiated on the knob.
5. Toggle a selected light and change brightness. Home Assistant and the S3 UI
   must converge.
6. Restart only the ESP32. The S3 must remain operable, temporarily use direct
   service fallback, then return to bridge-ready after reconnect.
7. Set one S3 target to a different entity. Bridge readiness must turn off and
   the direct S3 route must remain functional.
8. Change the weather entity state in Home Assistant. Temperature, humidity,
   wind, condition and location must converge while protocol errors stay zero.
9. Open the temperature context. It must show 08/13/19/23 o'clock plus compact
   daily summaries for tomorrow and the following day. The coprocessor status
   must report `ESP32 HA-Bridge + Forecast aktiv`.
10. Compare tomorrow and the following day with Home Assistant. Cloudy,
    partly-cloudy, fog and wind must use visibly different symbols. A question
    mark is a diagnostic failure and must correspond to an
    `Unbekannter Tages-Forecast` warning in the ESP32 log.
11. Open Radar and confirm the cached image appears immediately. Trigger three
    reloads at least one second apart; every request must replace the image in
    under one second on the local network, `S3 Radar Proxy Status` must reach
    `Bild aktiv`, the byte counter must be greater than zero and both protocol
    error counters must remain unchanged. A proxy error must preserve the last
    valid image and activate the original direct S3 path instead of blocking
    the UI.
12. Open the media picker and compare playlists, radios and podcasts with the
    existing Music Assistant lists. `S3 Library Proxy Status` must report all
    three received lists in sequence and both protocol counters must stay zero.
13. Open Light details for a WLED entity. Its saved Home Assistant preset
    options must appear in the popup and the active option must be highlighted.
    Select a preset and confirm the ESP32 action counter increases once. With
    no WLED presets saved, both diagnostics and the popup must report the empty
    state without protocol errors.
14. After boot, confirm `S3 Playlist Cache Entries` and
    `ESP32 Playlist Cache Entries` converge to the same full catalog count
    without pressing `Weitere laden`. Scroll beyond the retained bootstrap
    boundary, select a playlist and confirm the title pages load automatically.
    Paging metadata must remain intact and both protocol counters must stay at
    zero. Selecting a transferred track must start the same URI as before.
15. Confirm `ESP32 Bridge Time Synced` becomes on within 15 seconds and
    `ESP32 Bridge Time Age` repeatedly returns near zero. On the ESP32,
    `S3 Time Sync Acknowledged` must also be on and its acknowledgement age
    must return near zero every ten seconds. The centered clock, alarms, timer
    and screensaver clock must continue without a visible jump.
16. Compare `S3 Battery Percentage via Bridge` and `S3 Battery Voltage via
    Bridge` on the ESP32 device with the local S3 battery values. Disconnect
    and reconnect external power; `S3 External Power via Bridge` must follow
    within 16 seconds while both UART protocol counters remain unchanged.
17. Exercise previous and next from the legacy media control entry point. Each
    press must increase `ESP32 HA Bridge Actions` exactly once. Press `all
    lights off` only in a prepared test scene; it must add one bridge action
    per configured light and must not require S3 Wi-Fi. Repeat after stopping
    the ESP32 and confirm the direct S3 rescue services still work.

## Performance stage 1

Revision `.55` / `.21` makes the migrated ESP32 route the normal operating
path. The S3 retains associated Wi-Fi, API and OTA components for recovery, but
keeps its MQTT client disabled while the bridge is healthy. Bridge loss or a
proxy rejection activates the direct compatibility path; a stable bridge
disables it again after 30 seconds. UI-side UART work is bounded, repeated
diagnostic states are coalesced and bulk image decode waits for an idle window.
The decorative second-dot redraw is disabled in this profile because its
display flush introduced a measured recurring scheduler gap near 120 ms.
Media play requests receive an immediate `accepted` result and, where the HA
action supports it, a final success or error. The S3 keeps a blocking progress
view visible for a four-second settling window after acceptance. An explicit
error wins; an absent optional final callback no longer produces a false
timeout. If even bridge acceptance is absent, the modal stays protected until
the 15-second timeout and displays `START UNKLAR`. Playlist selector updates
run on the S3 only when the ESP32 request proxy is unavailable.

Acceptance tests and latency limits are in
[`stage1-responsiveness-test-catalog.md`](stage1-responsiveness-test-catalog.md).

## Next migration steps

The remaining work is consolidated into four release milestones:

1. qualify `.80` / `.39` as the final compatibility baseline;
2. migrate all remaining Home Assistant state and HTTP asset paths;
3. remove normal S3 network consumers and retain deliberate rescue/OTA only;
4. pass the 72-hour regression gate and freeze the production candidate.

The authoritative roadmap is
[`final-migration-roadmap.md`](final-migration-roadmap.md); the exact remaining
subscriptions are tracked in
[`s3-network-dependency-inventory.md`](s3-network-dependency-inventory.md).
