# Dual-MCU Performance Framework

This document defines the implemented compatibility architecture and the safe
path toward further offload on the JC3636K518C. Firmware 1.2.0 behavior remains
the compatibility contract. The production device named
`passion_wave_rotaryknob` is outside the test scope and must not be modified.

## Current implemented revision

Revision `1.2.0-ui-next.98` / `1.2.0-ha-bridge.50` runs on the second physical
device:

- the ESP32-S3 retains the complete 1.2.0 application, native Home Assistant
  API, Wi-Fi, MQTT, HTTP, display, touch, haptics, media, weather, timer and
  alarm features;
- EC1 is acquired on the S3 by two hardware PCNT units and is the only encoder
  path allowed to change UI state;
- the ESP32-U4WDH captures EC2 for comparison, maintains its own Home Assistant
  connection, executes migrated media/light actions and mirrors their compact
  states to the S3 over UART, including media progress, shuffle and repeat;
- EC2 mismatch, link health, queue overflow and protocol errors are observable
  but cannot interrupt EC1 control;
- Bluetooth, BLE tracking, Bluetooth proxying and Improv are absent.

This revision completes performance stage 1. The S3 keeps Wi-Fi, native API and
OTA for maintenance and deliberate recovery, but does not start MQTT, HTTP or
direct integration refreshes in normal operation. A rejected proxy operation
or bridge loss reports an explicit unavailable state; only the non-persistent
`S3 Network Rescue Mode` activates the compiled compatibility path. S3 Wi-Fi
remains enabled for API, OTA and that deliberate rescue path.

Stage 1 also bounds S3 UART work to eight frames per 2 ms scheduling slice,
coalesces diagnostic publication to 1 Hz, delays cover downloads until 2.5
seconds without interaction and performs radar decode only in an idle UI
window. `S3 UI Scheduler Gap` reports the largest scheduling gap in each
one-second window; `S3 Compatibility Network Fallback` shows whether the
temporary direct path is active.

Revision `.51` removes the decorative per-second orbit-dot refresh from the
performance profile. It forced an otherwise unnecessary display flush of about
120 ms. Clock and date labels now update on minute boundaries; timer and alarm
logic still ticks every second.

State changes are still pushed immediately, while the redundant full reconnect
snapshot cadence is reduced from 5 to 60 seconds. Clock redraws and diagnostic
publication wait for an interaction-free window, and a not-yet-populated ESP32
library cache is retried without waking the S3 MQTT fallback.
Resetting the encoder diagnostics now also resets both UART statistics, so a
startup partial frame is excluded from the measured test window.

Revision `.52` / `.21` optimizes the media picker. Cached content is painted
before a page request, immutable row geometry is configured only once and
rotary movement normally updates only the old and new selection row. A full
16-row update now occurs only at a virtual-page boundary. Visual feedback is
painted before haptics and paging work. Media selection remains modal and shows
the chosen item until the ESP32 first acknowledges queue admission and then
reports the final Home Assistant result. A 15-second timeout replaces an
unbounded wait. Normal playlist selection no longer calls the S3-side
`input_select`; that legacy action is restricted to deliberate Rescue mode.
Revision `.53` treats the immediate ESP32 queue acknowledgement as the reliable
transport confirmation. Because some Home Assistant actions do not invoke the
optional final ESPHome callback, the modal closes after a four-second settling
window unless an explicit error arrived. A missing bridge acknowledgement is
shown as the short, display-safe message `START UNKLAR`.
Revision `.54` places the five main-navigation icon centers on the right-hand
display arc. Labels are right-aligned and end seven pixels before their icon.
The former edge markers are removed; active icon and label color provide the
selection state without introducing vertical artifacts.
Revision `.55` makes the five navigation button backgrounds fully transparent;
their full-size invisible touch targets remain unchanged.
Revision `.98` enlarges the media-picker Home target from 36 x 36 to
60 x 48 pixels and moves it away from the curved right edge. The visible house
stays compact, so the modal retains its quiet geometry while becoming reliably
touchable.
Revision `.56` establishes the second migration boundary for the media library.
Playlist, radio, podcast and track payloads are parsed exclusively on the
classic ESP32 during normal operation; S3 MQTT callbacks and the old direct
playlist selector remain compiled only for deliberate Rescue mode. A
temporarily unready ESP32 cache cannot activate that path. The weather
temperature label also reserves sufficient glyph space for an unclipped degree
sign at the existing 88 px type size.
Revision `.57` prebuilds the media-picker geometry outside the interaction
path and keeps the popup hidden until its complete frame is composed. Legacy
auxiliary views suppress the main navigation rail and expose only their local
controls. Starting the screensaver closes transient radar/settings workspaces;
wake returns to UI Next weather instead of restoring them.

Revision `.97` / `.50` upgrades the inter-processor protocol to version 3 with
a 192-byte bounded payload and 186-byte image chunks. Radar is prefetched after
bridge readiness and has priority over queued decorative assets. Asset retry
cooldowns are independent, so a failed photo or cover request cannot impose its
30-second cooldown on radar. Two S3 image buffers preserve the visible cached
frame while the replacement is transferred and decoded; the active buffer is
swapped only after a successful decode. Opening a cache younger than 60 seconds
does not start a redundant transfer or decode; older caches update in the
background. Explicit user reloads are never held by the passive refresh
throttle. On the installed test device, three consecutive final
radar requests completed in 0.68–0.75 seconds with zero UART/protocol errors,
zero encoder queue overflows and a 4 ms steady-state UI scheduler gap. A separate
transaction watchdog detects and requeues the otherwise silent request reset
that can occur during a bridge-capability transition at boot. The ESP32 also
abandons a transfer after 12 seconds without acknowledgement, preventing a
rebooted S3 from leaving the server permanently busy.

## Processor boundary

### ESP32-S3: UI, peripherals and authoritative input

The S3 owns:

- the 360 x 360 QSPI display and all LVGL objects;
- CST816 touch, DRV2605 haptics and display power state;
- EC1 on GPIO7/GPIO8 using hardware PCNT;
- battery ADC and peripherals wired only to the S3;
- compressed-image decode and final display buffers;
- page selection, immediate interaction feedback and the complete 1.2.0
  network behavior during the compatibility stage.

Exactly one application path manipulates LVGL. Encoder acquisition itself is
hardware-backed and remains active during UI or network stalls.

### ESP32-U4WDH: diagnostic coprocessor and future network owner

The ESP32 currently owns:

- EC2 interrupt capture on GPIO22/GPIO19;
- UART framing, heartbeat, ping and health telemetry;
- its own Wi-Fi and native Home Assistant connection;
- media and four-light state caches;
- migrated previous/play-pause/next/volume and light on/off/brightness actions;
- dedicated low-latency volume transport with immediate optimistic S3 paint,
  latest-value ESP32 dispatch and correlated HA confirmation;
- migrated current weather temperature, humidity, wind, condition and location;
- migrated daily/hourly forecast parsing and compact forecast snapshots;
- migrated radar HTTP download with acknowledged chunk streaming to the S3;
- MQTT parsing and bounded caches for the retained playlist, radio and podcast
  bootstrap lists, transferred to the S3 with acknowledged binary records;
- paginated playlist and playlist-track response parsing, bounded accumulation
  and metadata-preserving snapshots;
- outbound playlist and playlist-track page requests received as compact UART
  commands and published to MQTT on the network processor;
- exclusive normal-operation ownership of media-library JSON parsing and
  selection resolution; the S3 route is restricted to explicit fallback;
- reconnect snapshots and bridge readiness.

EC2 is not a fallback or authoritative input because device measurements show
non-unit jumps and substantially worse behavior than EC1. It remains useful for
hardware investigation and redundancy qualification.

Future stages may move the remaining HTTP streaming to this processor. Its
4 MB flash and lack of
external PSRAM require bounded records and streaming rather than large JSON or
image buffers.

## Encoder architecture

The knob produces directional pulses, not quadrature phases:

| Path | Left / counter-clockwise | Right / clockwise | Runtime role |
| --- | --- | --- | --- |
| EC1 | S3 `GPIO7` (`EC1_B`) | S3 `GPIO8` (`EC1_A`) | authoritative |
| EC2 | ESP32 `GPIO22` (`EC2_B`) | ESP32 `GPIO19` (`EC2_A`) | diagnostic |

EC1 uses two independent S3 PCNT units. Falling edges increment hardware
counters behind a 10 microsecond glitch filter. Overflow accumulation is
enabled, and counters are sampled without being cleared. A 10 ms UI interval
subtracts the previous snapshots and feeds `right - left` into the unchanged
1.2.0 page logic.

```text
GPIO7 falling edge -> left PCNT counter +1
GPIO8 falling edge -> right PCNT counter +1
10 ms UI cycle     -> steps = right_delta - left_delta
```

This separates realtime acquisition from LVGL and network scheduling. Home
Assistant statistics publish only once per second. The dual-MCU overlay copies
the accumulated EC1 diagnostic total to the UART comparison channel at 10 Hz.

EC1 and EC2 must never be added. They represent the same mechanical detent.
Resetting test counters changes only a diagnostic origin; it neither clears the
active PCNT units nor creates a pulse-loss window.

See [`rotary-recognition.md`](rotary-recognition.md) for failure analysis,
implementation details and encoder acceptance criteria.

## Inter-processor link

| Direction | ESP32-S3 | ESP32-U4WDH |
| --- | --- | --- |
| S3 to ESP32 | `GPIO38` TX | `GPIO18` RX |
| ESP32 to S3 | `GPIO48` RX | `GPIO23` TX |

The implemented link runs full duplex at 2,000,000 baud, 8N1. It uses binary
COBS-delimited frames containing protocol version, message type, flags,
sequence number, payload length and CRC-16. JSON is not used between
processors. Heartbeat, ping/pong, encoder diagnostics and counter reset are
implemented.

UART logging must not share this link. Both receivers use bounded queues and
report decoding, CRC, version and overflow errors.

## State ownership

Every mutable value has one owner:

- EC1 pulse acquisition and encoder authority: S3;
- EC2 raw diagnostic count: ESP32;
- active page, selection, display and haptic policy: S3;
- migrated Home Assistant truth and retry state: ESP32, with deliberate S3
  Rescue mode;
- UART link statistics: local to each endpoint.

Only after a future feature has an implemented ESP32 equivalent, reconnect
snapshot, failure behavior and regression test may its network ownership move
off the S3.

## Scheduling and memory rules

### S3

- Keep all LVGL calls in the existing application context.
- Keep PCNT acquisition free of allocation, logging, network publishing and
  UART writes.
- Coalesce UI refreshes; do not perform one network update per encoder pulse.
- Put large decoded images and inactive assets in PSRAM.
- Keep UART rings, DMA descriptors and realtime state in internal RAM.

The Version-2.0 memory audit applies these rules concretely:

- raw media-library JSON is discarded after parsing; only bounded records and
  paging metadata remain;
- the obsolete nine-entry S3 WLED cache is removed; the popup reads only the
  generic 32-entry light-detail catalog;
- the light-detail popup owns eight LVGL rows and moves a virtual window over
  at most 32 labels, avoiding 32 permanently allocated button trees;
- UI Next reparents the reusable media picker to the top layer and then deletes
  the unused legacy Light, Media and Weather object trees;
- large clock fonts contain only the digits and punctuation they render;
- non-persistent selection and editor indices no longer write flash-backed
  preferences;
- the compressed UART asset buffer is released immediately after decode;
- radar and floorplan pixel buffers are released 45 seconds after leaving
  their page, so the next visit obtains a current image; the static photo
  buffer is released after 30 seconds. Active or queued transfers block
  release.

This policy deliberately keeps realtime UART, encoder and LVGL working state
in internal RAM. PSRAM placement itself is unchanged because decoded images
still need it while visible; only their lifetime is shortened.

### ESP32

- Keep the EC2 ISR limited to timestamp/direction capture in a bounded ring.
- Never block encoder draining on Wi-Fi, API, MQTT or UART transmission.
- Use fixed-capacity queues and reject oversized protocol records.
- Stream future HTTP payloads in chunks; do not accumulate complete images.

## Performance and stability gates

| Metric | Acceptance target |
| --- | --- |
| EC1 lost or duplicated detents | zero |
| Encoder batch sampling period | 10 ms nominal |
| Visible/haptic response, p99 | under 25 ms on active pages |
| S3 UI scheduler gap during active interaction | no sample above 25 ms |
| EC1 PCNT read errors | zero |
| UART CRC/frame errors | zero during 24-hour test |
| Coprocessor loss affecting EC1 UI | zero occurrences |
| Unplanned resets | zero during 72-hour mixed-load test |

The implemented synthetic input benchmark now measures the complete
S3 -> ESP32 -> Home Assistant -> ESP32 -> S3 loop. Its clean 25-sample
post-rollback acceptance run reached 9.528 ms p50 and 14.238 ms p95 with zero
timeouts and zero UART protocol errors. One HA/Wi-Fi tail sample reached
31.566 ms while UART latency stayed around 1 ms and the S3 scheduler gap stayed
at 5 ms. See
[`end-to-end-latency-benchmark.md`](end-to-end-latency-benchmark.md) for the
measurement contract, entities, rejected alternatives and reproduction steps.

Validate slow one-detent movement, repeated fast spins, reversals, active image
downloads, Home Assistant traffic, dimming and sleep wake-up. Separately regress
all 1.2.0 functions listed in the installation guide.

## Remaining delivery milestones

The remaining migration is deliberately grouped into four larger releases:

1. qualify the `.80` / `.39` compatibility baseline;
2. complete ESP32 ownership of all Home Assistant state and HTTP asset paths;
3. remove normal S3 network consumers while retaining deliberate rescue and
   independent OTA;
4. complete the 72-hour release gate and freeze the final processor boundary.

The detailed scope, acceptance gates and rollback points are maintained in
[`final-migration-roadmap.md`](final-migration-roadmap.md).

Manual build, flash and Home Assistant steps are documented in
[`dual-mcu-test-installation.md`](dual-mcu-test-installation.md).
The productive bridge and its fallback contract are documented in
[`dual-mcu-ha-bridge.md`](dual-mcu-ha-bridge.md).
The complete stage-1 regression and responsiveness matrix is documented in
[`stage1-responsiveness-test-catalog.md`](stage1-responsiveness-test-catalog.md).
