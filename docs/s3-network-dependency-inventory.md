# S3 network dependency inventory

The current product release is Version `2.1.1`
(`responsiveness,nextUI`). Internal revisions `.98/.50`, `.80/.39` and
`.83/.45` below are historical migration checkpoints, not customer-facing
versions. The production device remains on its unchanged 1.2.0 configuration.

## Direct Home Assistant subscriptions

The inherited S3 firmware still declares 32 Home Assistant subscriptions:

| Group | Declared | Mirrored by ESP32 | Still awaiting migration |
| --- | ---: | ---: | ---: |
| Time | 1 | 1 | 0 |
| Media | 13 | 13 | 0 |
| Lights | 11 | 11 | 0 |
| Weather | 6 | 6 | 0 |
| Radar image path | 1 | 1 | 0 |
| **Total** | **32** | **32** | **0** |

The 32 mirrored subscriptions intentionally remain compiled into the S3 test
profile for the current rescue path. Their callbacks are already suppressed
while the corresponding bridge readiness flag is active, but the ESPHome API
still receives the state traffic. They may be removed from the test overlay
with list-ID `!remove` entries only after the mixed-load qualification gate.

The five dependencies below were the final Milestone-2 gap and are mirrored by
the ESP32 in `.83` / `.45`:

- light 1 colour temperature;
- legacy light 4 preset and RGB state;
- current-weather precipitation probability;
- direct radar image path used by the rescue downloader.

Their inherited S3 subscriptions remain compiled for the Milestone-2
compatibility fallback. With a healthy bridge, callback guards prevent these
states from changing UI state. Milestone 3 removes the subscriptions.

UI Next light-detail discovery is also network-owned by the classic ESP32 in
Version 2.0. It resolves same-device WLED preset selects and same-area Hue
scenes, keeps command values on the ESP32, and sends an atomic label catalog to
the S3. The S3 performs no direct discovery or light-detail action during
healthy dual-MCU operation. Its equivalent Home Assistant template/action path
is retained only for the standalone image and deliberate Rescue mode.

## Direct S3 HTTP and MQTT

Five on-demand image decoders remain on the S3:

- media cover, 256 x 256;
- media-page cover, 124 x 124;
- radar image rescue path;
- photo slideshow;
- house floorplan.

With a healthy bridge, radar, media artwork, slideshow photos and the house
floorplan all receive compressed bytes through the acknowledged ESP32 asset
proxy; none starts S3 HTTP. The decoder components remain compiled so the same
UI objects can consume the proxied bytes and so Milestone 2 still has a
bridge-loss compatibility path. Media artwork uses a 256-pixel Music Assistant
source, the smallest size accepted by the active provider.

The S3 MQTT client remains disabled during normal operation. It is retained
only for deliberate, non-persistent `S3 Network Rescue Mode`; a proxy failure
alone does not start it.

## Control-path closure in revision .71

The legacy media previous/next handlers and the `all lights off` handler now
use the existing low-latency UART action protocol whenever bridge readiness is
true. Direct S3 Home Assistant services execute only while the bridge is down.
No new protocol record was required, and UI state is still updated locally
before network dispatch.

Revision `.72` fixes two UI state handovers found during qualification:

- previous/next resets media progress optimistically to zero and rejects stale
  pre-change position feedback for up to six seconds. The UI progress clock
  continues locally during that guard and valid near-zero feedback releases it
  immediately;
- selecting a dynamic or static WLED preset closes the preset-selection mode
  and returns the encoder directly to brightness control.

Revision `.73` starts the next media-metadata migration stage:

- the ESP32 now owns and mirrors the media-player friendly name and album
  artist; the S3 keeps its inherited subscriptions only as a rescue path;
- playlist page zero is also exposed as the compact startup list, preventing
  the old kind-1 request from starving the paged kind-4 cache;
- cache states `not ready` and `busy` are retried without waking S3 MQTT;
- the S3 reports the parsed list kind and entry count back to the ESP32, making
  end-to-end library loading observable in Home Assistant.

Revision `.74` completes media metadata ownership:

- the ESP32 subscribes to all three possible artwork attributes, applies the
  same source priority and Music Assistant image-proxy normalization centrally;
- resolved URLs up to 512 bytes are transferred in bounded, ordered UART
  chunks. The S3 acknowledges the complete URL before it enters the existing
  image pipeline;
- only one URL chunk is emitted per cooperative loop pass, after encoder and
  control traffic, so artwork changes cannot block interactive input;
- the inherited S3 artwork subscriptions and downloader remain available only
  in deliberate Rescue mode. Actual artwork bytes use the ESP32 stream.

Revision `.76` closes the playlist-selection race:

- every newly selected playlist receives a non-zero generation that accompanies
  the S3 page request, ESP32 MQTT request and returned binary track page;
- the ESP32 accepts only the exact outstanding MQTT request ID, so a delayed
  response cannot replace the latest track cache;
- the S3 compares the returned generation before updating its list or consuming
  the `autoplay first track` flag. Stale pages are discarded and reported,
  while the pending bit remains open until the matching generation arrives.

Revision `.77` removes the slow post-reboot library path:

- an S3 `HELLO` now cancels only the ESP32's obsolete in-flight transfer while
  retaining all completed caches, preventing an old unacknowledgeable transfer
  from blocking the new session;
- the retained compact playlist list is mirrored into the paged cache during
  ESP32 cold boot, so opening the picker does not require a fresh HA service
  response;
- the S3 preloads the paged playlist cache first and treats it as satisfying
  the redundant compact-list requirement. Track pages retain highest priority.

Live S3-only OTA restart qualification on the test device:

- ESP32/S3 link restored at `t=30.757 s`;
- playlist transfer started at `t=31.786 s`;
- all 40 cached playlists were confirmed at `t=32.411 s`;
- playlist availability therefore followed the restored link after `1.654 s`,
  of which `0.625 s` was the acknowledged UART transfer;
- radio and podcast caches followed without blocking the playlist, and the
  UART protocol error counter remained at zero.

Revision `.78` / bridge `.38` fixes playlist queue ownership:

- selecting a playlist now sends the playlist itself to Music Assistant instead
  of starting track zero as an isolated item;
- the ESP32 uses `enqueue: replace` for both compact and paged playlist kinds,
  while tracks, radio stations and podcast episodes retain `enqueue: play`;
- the playlist track page is still loaded for browsing, but it can no longer
  trigger a second playback action or overwrite the queue created by Music
  Assistant;
- successful playlist dispatch is acknowledged after the Home Assistant action
  completes. Player readiness does not compare the current track URI with the
  playlist URI because Music Assistant correctly exposes the first track as
  the active media item.

Live end-to-end qualification on the test device:

- Home Assistant confirmed S3 `.78` and ESP32 `.38` as the active firmware;
- the S3 diagnostic request arrived at the ESP32 as
  `play_ok:4:0:Eintrag 1`, proving the paged-playlist route over UART;
- bridge acceptance took `4.752 ms`, the Home Assistant/Music Assistant action
  completed after `1158.158 ms`, and the S3 reported the player ready after
  `1166.700 ms`; the repeated probe after the final fallback build completed
  after `1195.475 ms`;
- the selected 94-track playlist replaced the former 290-item queue and started
  with `Time`;
- two consecutive Next actions produced `Now We Are Free` and
  `Dream Is Collapsing`, matching playlist positions two and three;
- the existing UART error counter stayed unchanged during both playback probes
  and all Next operations;
- the test player remained at volume zero and was paused after qualification.

Revision `.79` fixes non-zero playlist acknowledgement correlation:

- the S3 now retains the selected playlist's canonical list index while the
  asynchronous Music Assistant start is pending;
- previously this field was always zero, so a successful result such as
  `kind=4 index=9 code=0` started playback but did not clear the modal. Its
  15-second watchdog then displayed the misleading `START UNKLAR`;
- the Music Assistant diagnostic probe now uses playlist index 9 and exercises
  the same pending UI state. Its status includes `match=1` or `match=0`, making
  future correlation regressions directly observable in Home Assistant.

Home Assistant media-picker scheduling was qualified and corrected alongside
revision `.79`:

- the single media-bridge automation previously used `mode: queued`. A large
  playlist-track request, such as the 620-entry Asterix list, could therefore
  keep a later 24-entry playlist-page request waiting for several minutes;
- the bridge now uses `mode: parallel` with isolated per-trigger variables.
  Playlist pages, track pages and the periodic static-cache refresh no longer
  block one another;
- the three top-level trigger selections use Home Assistant's native
  `condition: trigger` form instead of template comparisons;
- a live playlist-page trace completed the Music Assistant query and MQTT
  response in about 30 ms. Before the change, one observed request waited about
  6.5 minutes for its turn in the shared queue;
- stale local `esphome logs` processes must not be left attached to the test
  MCUs. Nine orphaned streams exhausted the useful API connections during the
  incident. After removing them, Home Assistant reconnected and the S3 restored
  its cached `P 40 · R 3 · O 40` library state with zero UART protocol errors.

Revision `.80` / bridge `.39` makes track pagination constant-cost:

- the first 16-title page completed normally, but requesting offset 16 caused
  the classic ESP32 to disappear before it could publish `Track-Seite 16`;
  Home Assistant had already returned the correct 16 records in 389 ms, proving
  that neither Music Assistant nor the automation queue caused the stall;
- the former proxy accumulated all earlier track pages, rebuilt the complete
  binary list and copied that growing blob for every UART transfer. This
  quadratic allocation and transfer path exhausted the network processor while
  processing the second Asterix page;
- track responses are now delta pages. The ESP32 retains and transfers only the
  newly returned page, including its offset, total and continuation flag. The
  S3 appends the page to its UI cache and replaces an already received offset
  idempotently;
- playlist pages remain cumulative on the ESP32 because it must resolve the
  selected global playlist index without involving Home Assistant;
- the S3 rejects page gaps explicitly and resets the pending loading state
  instead of leaving `Weitere werden geladen` on screen indefinitely;
- both images compile successfully with ESPHome 2026.7.0 and are installed on
  the test device as S3 `.80` and ESP32 `.39`. The mounted Device Builder copies
  contain the same revisions.

## Consolidated migration queue

State and asset ownership are implemented through `.98/.50`. Remaining work is
release qualification rather than another feature-sized migration:

1. verify clean boot, both independent OTA routes and deliberate rescue mode;
2. run the complete functional/latency catalog under mixed load;
3. complete the 72-hour endurance and injected-failure run;
4. freeze protocol compatibility, rollback artifacts and the retail installer.

Scope, exit gates and rollback points are defined in
[`final-migration-roadmap.md`](final-migration-roadmap.md).
