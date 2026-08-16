# Dual-MCU Home Assistant bridge

Current coordinated implementation: `3.0.0-beta.16`.

One physical Passion Wave Rotaryknob contains two processors. They share one
product generation but keep separate firmware images, native API identities
and recovery paths.

## Processor ownership

| Processor | Owns | Does not own in normal operation |
| --- | --- | --- |
| ESP32-S3 display | EC1 encoder, touch, LVGL, haptics, local optimistic UI, timers, alarms, display protection and image decoding | Home Assistant command dispatch, Music Assistant library access or normal asset downloads |
| Classic ESP32 Bridge | Home Assistant-facing state, bounded command envelopes, weather, media library paging, light details and HTTP asset downloads | Display rendering or authoritative EC1 input |
| PassionWave integration | Device assignment, target validation, Music Assistant calls, Home Assistant actions, runtime synchronization and coordinated update sequencing | Direct display rendering or inter-MCU transport |

The S3 retains Wi-Fi only for provisioning, encrypted ESPHome Native API, OTA
and diagnostics. Managed V3 compiles neither MQTT nor an S3 application-network
rescue path.

## Runtime paths

State and command flow:

```text
Home Assistant / Music Assistant
  ↕ validated local calls
PassionWave integration
  ↕ encrypted ESPHome Native API
classic ESP32 Bridge
  ↕ 2 Mbit/s framed UART (COBS, CRC, priorities, acknowledgements)
ESP32-S3 display, encoder and touch
```

Commands originate as bounded kind/index/value records on the S3. The Bridge
publishes a sequenced command state; the PassionWave integration validates the
command against that physical device's Config Entry, executes only the allowed
Home Assistant or Music Assistant action and returns a named response action.
Broad ESPHome Home Assistant action permission remains disabled.

State snapshots travel in the opposite direction. The Bridge sends changed
media, light, weather, connection and catalog records immediately and a
periodic complete snapshot as loss recovery. The S3 updates preallocated UI
objects and keeps short optimistic holds for volume and light brightness so a
late callback cannot visibly undo the user's current input.

For media there is exactly one authority: the PassionWave integration creates
an ordered snapshot containing state, title, artist, player label, volume,
position, duration, playback options and cover URL; the Bridge caches and
forwards it over UART. Dual-MCU firmware contains no compile-time media-player
subscription and executes no direct Home Assistant or Music Assistant action.
The S3 runtime diagnostics are read-only observations published after UART
receipt, not a second writable desired-state path.

## Media and library

The Config Entry owns the selected Music Assistant instance and player.
PassionWave provides bounded playlist, radio, podcast and playlist-track pages.
The S3 prefetches with five rows remaining; one request-in-flight guard and
generation-tagged responses prevent duplicate or stale page commits.

Media controls use compact commands for previous, play/pause, next, volume,
shuffle, repeat and library selection. The Bridge never accepts an arbitrary
entity ID from the S3; targets come from the Config Entry and authoritative
Bridge cache.

Library playback is coordinated per Config Entry with latest-command-wins
semantics. Every accepted choice receives a local generation; pending older
choices collapse to the newest target and only one Music Assistant service call
runs at a time. A stale generation can neither clear a repeated identical
choice nor send its final callback. Individual tracks use the Music Assistant
`replace` enqueue mode, and the integration confirms their
`media_content_id` with one bounded retry. A newer choice interrupts that
confirmation loop within the 100-ms poll interval. This keeps the final player
state deterministic even when a previous playlist is still preparing its
queue.

## Cover pipeline

The integration sends the selected player's state, title, artist and resolved
cover URL to the Bridge. The Bridge normalizes Music Assistant image-proxy URLs
and transfers the URL to the S3. Compressed cover bytes are downloaded by the
Bridge and sent through the acknowledged UART asset stream; the S3 decodes them
after active input has been quiet.

Fullscreen cover entry requires all of the following:

- media runtime state is `playing`;
- the resolved cover URL is non-empty;
- either page or fullscreen cover decoding is ready;
- no media picker or track selector is open;
- the display is awake;
- at least ten seconds have passed since the cover deadline and the last user
  input.

Useful diagnostics are `ESP32 Media Cover URL Status`, `ESP32 Media Cover Proxy
Status`, `Rotaryknob Media Runtime State`, `Rotaryknob Media Runtime Cover URL`
and `scrollwheel Media Debug Status`. The runtime diagnostics now prove what
the S3 actually received. The live beta.12 cover regression and its OTA retest
are tracked as `PW-UI-003` in `known-issues.md`.

## Lights

Each Config Entry owns up to four ordered light slots. On/off and brightness
snapshots are authoritative on the Bridge. Hue scenes and WLED presets are
resolved there, transferred as generation-tagged label catalogs and activated
only by validated slot/index commands. External Home Assistant changes must
converge back to the display without overwriting an active local brightness
hold.

## Weather and assets

The Bridge owns current weather, daily forecasts and the retry for a missed
startup forecast. Radar, floorplan, photos and media covers share one bounded
asset transport. Control and state frames have priority over bulk chunks; URL,
HTTP, size, timeout, CRC and decoder failures are reported without blocking
navigation.

The weather photographs are compiled into the S3 and selected locally from the
Bridge condition, so the normal weather screensaver needs no image download.

The managed S3 configuration removes inherited direct Home Assistant state
subscriptions and replaces the standalone media, weather and light fetchers
before ESPHome code generation. Consequently the managed S3 binary contains
no Home Assistant service-call objects; only the Bridge publishes bounded
command envelopes for the PassionWave integration.

## Recovery behavior

- Bridge loss leaves encoder, touch, local UI, timer, alarm and display
  protection operational. Remote features show an unavailable state and do not
  start a fallback network path.
- S3 restart triggers Bridge snapshots until runtime state and all four light
  catalogs converge again.
- Bridge or Home Assistant restart preserves the last complete UI data where
  safe and refreshes it after the API reconnects.
- Both processors retain independent encrypted API, OTA and serial recovery.
- Coordinated customer update order is Bridge → verified reconnect → S3 →
  verified reconnect. A Bridge failure stops before the S3 phase.

## Diagnostics and acceptance

The primary health signals are:

- `S3 Link Connected` and `ESP32 Coprocessor Link` on;
- `EC1 Encoder Ready` on;
- `EC1 Encoder Read Errors`, `UART Protocol Errors` and `Inter-MCU Protocol
  Errors` unchanged at zero after startup;
- finite link ping and bounded `S3 UI Scheduler Gap` during active input;
- matching runtime state on the selected Home Assistant player, Bridge and S3.

Execute the current live matrix in [Known issues](known-issues.md) and the
detailed [responsiveness test catalog](stage1-responsiveness-test-catalog.md)
for each physical Rotaryknob. A profile or Home Assistant entry alone is not
evidence that its corresponding processor has passed physical acceptance.
