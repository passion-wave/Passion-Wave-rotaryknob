# Dual-MCU Home Assistant Bridge

Product version `2.1.1` (`deterministic-onboarding,international-support`) is the current dual-MCU
workload split. The internal `.98` / `.50` counters remain historical test
checkpoints, not separate customer versions. The S3 owns deterministic input
and rendering. The classic ESP32 owns Home Assistant discovery, service calls
and bounded media/light state records.

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
- dynamic WLED preset and Hue scene catalogs for all four slots, including the
  active option and validated index-based activation;
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
original daily/hourly actions remain compiled for deliberate Rescue mode, but
do not resume automatically when a bridge record is late. Direct radar download
is likewise available only in Rescue mode.

Bridge `.10` adds the first bulk-data migration. The classic ESP32 downloads the
radar JPEG in a dedicated FreeRTOS task and streams it to the S3 in acknowledged
data chunks. Protocol version 3 raises the bounded frame payload to 192 bytes,
leaving 186 bytes per image chunk while keeping the encoded UART frame below
the one-byte COBS boundary. Version 2.0 schedules cover, radar and library data
through one shared 16 ms bulk slot after encoder, action and state processing.
The aggregate background stream is therefore capped at roughly 12 kB/s instead
of allowing cover or library traffic to bypass the older radar-only throttle.
A 64-frame receiver queue plus a 4 KiB UART receive buffer
absorbs short LVGL stalls without dropping image chunks. Per-frame
CRC-16, contiguous offsets, total length and an end-to-end CRC-32 protect the
image. Every begin, data and end frame is acknowledged; a missing or damaged
frame is retransmitted after 40 ms. The S3 reuses the existing runtime JPEG
decoder, so the radar widget and 320 x 320 display buffer are unchanged. A
12-second transfer timeout, invalid offset, CRC mismatch, HTTP error or decode
error preserves the last valid image and reports the affected asset kind. The
direct S3 download is available only when Rescue mode is explicitly enabled.

Revision `.50` / UI `.97` completes the responsive asset path. Retry cooldowns
are isolated by asset kind, so a missing photo, cover or floorplan cannot delay
radar. Radar warm-up takes priority over background decorative assets; an
explicitly opened House page may replace a not-yet-started radar warm-up and is
otherwise queued directly behind the active transfer. The bridge
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

The bridge resolves `.local` asset hosts with an explicit mDNS query before
starting the ESP-IDF HTTP client and caches the resulting IPv4 address.
Nevertheless, a numeric Home Assistant URL is the deterministic and fastest
choice for private installations. The private ESP32 wrapper must receive
`home_assistant_base_url`, all photo URLs and
`house_floorplan_image_url`; configuring these only on the S3 does not affect
the processor that owns the HTTP download. Error code `2` means HTTP connect
failed, while code `15` means the preceding `.local` mDNS lookup failed.

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
list has decoded successfully does the S3 commit the new cache. A changed
retained payload invalidates only its own feature bit and triggers a fresh
transfer. Link loss clears readiness and reports the missing bridge; it does
not restore the original S3 MQTT route unless Rescue mode is explicitly
enabled.

Paginated playlist and playlist-track requests still originate on the S3 in
this compatibility stage. Their JSON responses are parsed on the ESP32 from
bridge `.13` onward.

Bridge `.12` introduced a slot-specific WLED preset route with nine bounded
names. Version 2.0 replaced its S3 receiver and cache with one generic
light-detail catalog for all four light slots. The classic ESP32 still emits
the old frames temporarily so an ESP32-first rolling OTA can continue to serve
an older S3. A current S3 ignores them; they neither populate nor render the
light popup. An empty Home Assistant option list is represented explicitly and
does not create synthetic presets.

The active Version-2.0 light-detail path is:

- the classic ESP32 identifies WLED and Hue entities through Home Assistant;
- WLED discovery resolves the preset `select` on the same device;
- Hue discovery resolves up to 32 Hue scenes from the light's assigned area;
- command targets stay only in the authoritative ESP32 cache;
- the UART transports only slot, generation, kind, index and bounded labels;
- label records are cooperatively paced at 8 ms, keeping encoder/action frames
  ahead of even three simultaneous 27-scene Hue catalogs while completing the
  full warm-up in under one second;
- the S3 swaps the visible list only after the matching commit record proves
  the generation complete;
- a four-bit completion mask makes a rebooted S3 request recovery snapshots
  until every slot, including an intentionally empty slot, has committed;
- the ESP32 retains its last complete catalogs across an API interruption,
  waits 1.5 seconds after Home Assistant reconnects, and automatically retries
  malformed or failed response actions instead of publishing a transient empty
  result;
- selection returns only slot and index, which the ESP32 validates before a
  native `select.select_option` or `scene.turn_on` action.

`BRIDGE_STATUS` byte 1 bit `0x02` advertises this capability. An older S3
ignores the new records; an updated S3 keeps the compatibility route until the
new ESP32 advertises support. This is why rolling OTA installs the ESP32 image
first and the S3 image second.

Bridge `.13` owns JSON parsing for paginated playlist and playlist-track
responses. It accepts only request IDs belonging to the test S3 and sends
bounded delta pages containing offset, next offset and `has_more`. The S3
accumulates display names only after each page passes contiguous-transfer and
CRC-32 validation. The classic ESP32 keeps only a compact global URI/item-ID
index for playback and further track requests. This avoids the former
cumulative name/blob duplication and its heap peak on large catalogs. A proxy
timeout reports an explicit error. The original S3 response parser is available
only while Rescue mode is enabled.

Bridge `.14` adds index-based media selection. The S3 sends only the library
kind and selected index; the ESP32 resolves both against its canonical cache.
Bridge `.15` calls the native `music_assistant.play_media` action with the
resolved URI and reports success only after Home Assistant acknowledges the
action. Bridge `.16` corrected the configured target from a generic Sonos
entity to the corresponding native Music Assistant player. Transport controls
work on the generic entity, but Music Assistant library selection must address
the Music Assistant queue.
The S3 keeps a valid Home Assistant-selected runtime target across reboots.
Only an empty value or the public factory placeholder is replaced by the
compiled fallback. The former unconditional boot assignment could silently
restore an old player and make optimistic volume feedback jump to that
player's value.

The fast bridge path still requires the compiled S3 and ESP32 targets to match
the persisted S3 targets. Private test wrappers therefore override the same
native Music Assistant entity and the same four light entities in both
profiles. Local entity IDs belong in private configuration and are
intentionally omitted from this public architecture document.

That target match gates only actions and target-specific state. Bounded
playlist/track transport and page requests are target-independent capabilities:
the picker can continue browsing while a persisted media or light target
differs from the private wrapper. A temporary page-transport outage retains the
last accepted offset and continuation flag; the five-entry prefetch waits
without polling the network and resumes when the advertised capability returns.

Bridge `.17` moves the two remaining outbound library page requests. S3 `.47`
sends a fixed six-byte command containing list kind, offset, limit and selected
playlist index. The ESP32 resolves that index against its canonical cache,
constructs the existing request JSON and publishes it to MQTT. An immediate
result record distinguishes accepted MQTT publishes from invalid indices or a
disconnected broker. A rejected request produces a bounded error; the original
S3 MQTT path is available only after deliberate Rescue activation. Successful
responses continue through the existing bounded binary list transfer.

Bridge `.38` makes playlist playback an atomic queue replacement. Playlist
selection resolves the canonical playlist URI on the ESP32 and calls
`music_assistant.play_media` with `enqueue: replace`. The separately fetched
track page remains a browser view only. It no longer autoplays its first track,
which previously left an unrelated Music Assistant queue behind the selected
first item. S3 `.78` identifies this route explicitly as
`PLAYLIST_PAGE`; bridge `.38` accepts both playlist kind identifiers for
backward compatibility.

The paging path has been live-accepted with all 140 Music Assistant playlists,
including every entry after the 40-item retained bootstrap. Normal interaction
does not eagerly transfer that complete catalog: the S3 requests one bounded
page five cached entries before the user reaches the end. This keeps startup,
UART traffic and heap use bounded while hiding the Home Assistant/MQTT/UART
round trip behind continued scrolling. Playlist tracks use the same delta-page
scheme and are prefetched in bounded chunks while the ESP32 retains their
compact global URI index.

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
Existing S3 Home Assistant services remain compiled but resume only in
deliberate Rescue mode. Dynamic target changes therefore never send an action
to the wrong entity.

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
| `RADAR_ERROR` | ESP32 → S3 | bounded error code; Rescue remains explicit |
| `RADAR_ACK` | S3 → ESP32 | accepted transfer ID and next byte offset |
| `LIBRARY_REQUEST` | S3 → ESP32 | request bootstrap or paginated library cache |
| `LIBRARY_BEGIN/CHUNK/END` | ESP32 → S3 | bounded list transfer with total and CRC-32 |
| `LIBRARY_ACK` | S3 → ESP32 | accepted transfer ID and next byte offset |
| `LIBRARY_CHANGED/ERROR` | ESP32 → S3 | invalidate one cache or report an error |
| `LIGHT_DETAIL_CATALOG_ITEM` | ESP32 → S3 | slot/generation/index plus bounded WLED or Hue label |
| `LIGHT_DETAIL_CATALOG_META` | ESP32 → S3 | atomically commit kind, count and active index |
| `HA_ACTION: LIGHT_DETAIL_ACTIVATE` | S3 → ESP32 | activate authoritative catalog slot/index |
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
- `S3 Light Detail Catalog` (`W` = WLED, `H` = Hue, `-` = no supported detail).

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
- `ESP32 Light Detail Catalog` with the authoritative count for all four slots.
- `Refresh Light Detail Catalog`, a diagnostic button that invalidates only
  the discovery state and starts a fresh Home Assistant registry lookup. The
  last complete popup remains visible while that lookup is running.

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
6. Restart only the ESP32. The S3 local UI and EC1 input must remain operable,
   display unavailable network state and return to bridge-ready after reconnect
   without starting MQTT or direct actions.
7. Set one S3 target to a different entity. Bridge readiness must turn off and
   no target-bound network action may be sent until targets match again or
   Rescue mode is deliberately enabled. Playlist browsing must remain active:
   scroll beyond the 40-entry bootstrap and confirm that the next bounded page
   still arrives through the ESP32.
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
    `Asset aktiv: radar`, the byte counter must be greater than zero and both
    protocol error counters must remain unchanged. A proxy error must preserve
    the last valid image, identify `radar` rather than `none`, and leave the UI
    responsive.
12. Open House or call the S3 API action `house_refresh`. The proxy status must
    reach `Asset aktiv: house`, the byte counter must be positive and the live
    floorplan must replace the loading placeholder. Repeat directly after a
    radar refresh to verify single-flight queuing.
13. Open the media picker and compare playlists, radios and podcasts with the
    existing Music Assistant lists. `S3 Library Proxy Status` must report all
    three received lists in sequence and both protocol counters must stay zero.
14. Open Light details for a WLED entity in each of the four configurable
    slots. Its saved Home Assistant preset options must appear in the popup.
    Select a preset and confirm exactly one `select.select_option` action is
    executed by the ESP32. The WLED integration and the preset select are
    resolved from the Home Assistant device registry, not from the slot number
    or entity-name text.
15. Open Light details for a Hue entity. Only Hue scenes assigned to the
    selected light's Home Assistant area must appear. Select one and confirm
    exactly one `scene.turn_on` action is executed by the ESP32. A Hue light
    without an area, and a normal light without supported details, must show
    the empty-state text without protocol errors.
    Compare `ESP32 Light Detail Catalog` and `S3 Light Detail Catalog`; all
    four slot kinds and counts must be identical.
    Restart only the S3 while the ESP32 remains online. The S3 must request
    another snapshot and converge without restarting the ESP32. Reset the
    diagnostic counters after boot synchronization; both must remain zero
    across the following 60-second recovery snapshot.
    Then interrupt and restore only the ESP32 API connection. The existing
    detail rows must remain visible during the interruption and both catalog
    diagnostics must reconverge automatically. `Refresh Light Detail Catalog`
    provides the same lookup on demand without rebooting either MCU.
16. After boot, open the playlist picker and scroll with touch and encoder
    beyond the retained bootstrap and at least two page boundaries. Five
    entries before each S3 cache boundary, confirm that one bounded page is
    requested and `S3 Playlist Cache Entries` increases by the received page.
    The visible list must not stop or jump when the response arrives. Paging
    metadata must remain intact and both protocol counters must stay at zero.
    Selecting a transferred track must start the same URI as before.
17. Confirm `ESP32 Bridge Time Synced` becomes on within 15 seconds and
    `ESP32 Bridge Time Age` repeatedly returns near zero. On the ESP32,
    `S3 Time Sync Acknowledged` must also be on and its acknowledgement age
    must return near zero every ten seconds. The centered clock, alarms, timer
    and screensaver clock must continue without a visible jump.
18. Compare `S3 Battery Percentage via Bridge` and `S3 Battery Voltage via
    Bridge` on the ESP32 device with the local S3 battery values. Disconnect
    and reconnect external power; `S3 External Power via Bridge` must follow
    within 16 seconds while both UART protocol counters remain unchanged.
19. Exercise previous and next from the legacy media control entry point. Each
    press must increase `ESP32 HA Bridge Actions` exactly once. Press `all
    lights off` only in a prepared test scene; it must add one bridge action
    per configured light and must not require S3 feature networking. Repeat
    after stopping the ESP32: no direct command may be sent until
    `S3 Network Rescue Mode` is deliberately enabled; then verify the rescue
    service and disable Rescue again.

## Performance stage 1

Revision `.55` / `.21` made the migrated ESP32 route the normal operating
path. In current Version 2.0, the S3 retains Wi-Fi, API and OTA components for
maintenance and deliberate rescue, but keeps MQTT/HTTP and direct integration
actions disabled unless `S3 Network Rescue Mode` is enabled. Bridge loss or a
proxy rejection alone does not activate that path. UI-side UART work is
bounded, repeated
diagnostic states are coalesced and bulk image decode waits for an idle window.
The decorative second-dot redraw is disabled in this profile because its
display flush introduced a measured recurring scheduler gap near 120 ms.
Media play requests receive an immediate `accepted` result and, where the HA
action supports it, a final success or error. The S3 keeps a blocking progress
view visible for a four-second settling window after acceptance. An explicit
error wins; an absent optional final callback no longer produces a false
timeout. If even bridge acceptance is absent, the modal stays protected until
the 15-second timeout and displays `START UNKLAR`. Playlist selector updates
run on the S3 only in deliberate Rescue mode.

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
