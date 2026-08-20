# End-to-end input latency benchmark

The measurements in this document are historical qualification snapshots. The
current coordinated candidate is S3 and Bridge `3.0.1-beta.6`; re-run the
catalog on both physical devices rather than treating an older result as proof
for the current image.

## Purpose

The diagnostic benchmark measures the complete production-like control loop,
not just an inter-processor ping:

```text
S3 synthetic input
  -> 2 Mbit/s UART
  -> ESP32 Home Assistant bridge
  -> native HA input_button service
  -> subscribed HA state callback
  -> ESP32
  -> priority UART response
  -> S3 result
```

The input starts inside the same S3 automation context used by a local device
input. Triggering the benchmark button through Home Assistant is outside the
timed region. The following 25 samples are generated autonomously by the S3, so
the client invoking the test is not part of the result.

The direct service-to-state callback intentionally matches the production
media and light architecture. A second HA echo automation was evaluated and
rejected: it was not present in the production path and introduced avoidable
event-loop jitter.

## Home Assistant prerequisite

The benchmark uses exactly one native helper:

```text
input_button.passion_wave_latency_request
```

Create it as an `input_button` named `Passion Wave Latency Request`. No YAML,
template helper, polling automation or restart is required.

The helper is already present in the test Home Assistant instance. The ESP32
subscribes to its state and the S3 never opens a separate HA measurement
connection.

## Running the benchmark

In Home Assistant press the S3 device's button whose entity-ID suffix is:

```text
run_e2e_latency_benchmark
```

For one sample use:

```text
run_e2e_latency_probe
```

The 25-sample benchmark keeps intermediate results local and publishes only
the final summary. This prevents the diagnostic traffic from loading Home
Assistant while it is being measured.

Relevant entities:

| Entity suffix | Meaning |
| --- | --- |
| `e2e_local_dispatch` | S3 input handler through UART enqueue |
| `e2e_uart_round_trip` | S3 -> ESP32 -> S3 immediate control-frame round trip |
| `e2e_home_assistant_round_trip` | ESP32 service call through HA state callback |
| `e2e_total_round_trip` | complete S3 -> HA -> S3 loop |
| `e2e_benchmark_p50` | median of the 25 complete samples |
| `e2e_benchmark_p95` | 95th percentile of the 25 complete samples |
| `e2e_benchmark_maximum` | slowest complete sample |
| `e2e_probe_timeouts` | failed samples; acceptance value is zero |

## Implemented optimizations

- Both UART receive loops run every 1 ms instead of every 2 ms.
- Control frames are dequeued ahead of radar and library bulk frames while
  order within each traffic class stays stable.
- The ESP32 calls the helper directly and uses its subscribed state as the HA
  acknowledgement; no extra automation is in the measured production path.
- Each request carries a sequence number. Late, duplicate and concurrent
  results cannot complete the wrong measurement.
- The S3 and ESP32 use microsecond monotonic clocks locally. No wall-clock
  synchronization is required.
- Benchmark sensor updates are deferred until all 25 samples are complete.
- Wi-Fi power saving remains disabled on the ESP32.
- Native API encryption remains enabled; responsiveness does not weaken the
  security boundary.

`api.batch_delay: 0ms` was explicitly tested and rejected. It caused many
small packets and made HA latency substantially worse. ESPHome's default
batching remains active.

## Live acceptance result

Final test firmware:

- S3: `1.2.0-ui-next.66`
- ESP32: `1.2.0-ha-bridge.30`

Final post-rollback 25-sample run after resetting scheduler diagnostics:

| Metric | Result |
| --- | ---: |
| Successful samples | 25 / 25 |
| Timeouts | 0 |
| Total p50 | 9.528 ms |
| Total p95 | 14.238 ms |
| Total maximum | 31.566 ms |
| Last local dispatch | 0.042 ms |
| Last UART round trip | 0.971 ms |
| Last HA round trip | 11.296 ms |
| S3 scheduler maximum gap during run | 5 ms |
| UART protocol errors | 0 |

The initial implementation measured 15.387 ms p50 and 28.255 ms p95. The final
run therefore improves p50 by about 38% and p95 by about 50%. A preceding clean
run on the same final architecture measured 10.430 ms p50, 16.129 ms p95 and
17.786 ms maximum.

The final run had one 31.566 ms HA/Wi-Fi outlier above the 25 ms target. UART
errors remained zero, UART latency remained around 1 ms and the S3 scheduler
gap remained 5 ms, so this tail event was not caused by device processing or
bulk-frame head-of-line blocking.

## Remaining physical limits

The local dispatch is already around 0.05 ms and the normal priority-UART
round trip is about 1 ms. Further firmware polling reduction would increase
CPU scheduling pressure for little practical gain. The remaining variation is
primarily HA host scheduling and Wi-Fi/TCP delivery.

Do not remove API encryption, raise Wi-Fi transmit power without RF evidence,
or busy-loop either MCU. Those changes trade safety, coexistence or UI
stability for an unproven sub-millisecond gain.

## Music Assistant start latency

The test profile also provides a button with the entity-ID suffix:

```text
run_music_assistant_start_probe
```

This starts the first cached playlist through `music_assistant.play_media` on
the configured native Music Assistant test player. Before live validation the
player volume was explicitly set to `0.0`.

The path reports three distinct stages:

| Stage | Entity suffix |
| --- | --- |
| S3 -> ESP32 request accepted | `music_assistant_bridge_accept` |
| HA Music Assistant action completed | `music_assistant_service_completion` |
| matching content/playing state reached | `music_assistant_player_ready` |

`music_assistant.play_media` remains in use because a live comparison with the
generic `media_player.play_media` action was slower for this player. Media
selection actions now use `mode: restart`: a newer choice supersedes an older
unresolved choice instead of waiting in a queue. A valid `media_type` is sent
to Music Assistant, and final UI success follows the actual content/playing
state rather than only the service callback.

Measured muted results:

| Run | Bridge accept | MA service | Player ready at ESP32 | Complete at S3 |
| --- | ---: | ---: | ---: | ---: |
| Cold | 4.448 ms | 1483.433 ms | 1597.920 ms | 1602.649 ms |
| Warm 1 | 4.787 ms | 943.394 ms | 1145.627 ms | 1152.503 ms |
| Warm 2 | 5.065 ms | 989.569 ms | 1186.886 ms | 1193.657 ms |

The device and UART contribute about 5 ms. The remaining start time is owned
by Music Assistant queue/provider resolution and the physical player. The
lost-callback UI fallback was reduced from four seconds to 2.5 seconds, still
well above the measured 1.6-second cold start.

After validation the test playback was stopped. The test player remained at
volume `0.0`; both UART protocol counters and the encoder overflow counter were
zero in the final stable-state check.

## Encoder-to-volume software-in-the-loop benchmark

The volume benchmark injects a synthetic EC1 detent after hardware decoding
and then uses the same productive state, render, UART and Home Assistant path
as the physical encoder:

```text
decoded EC1 step
  -> optimistic S3 volume state
  -> minimal LVGL arc/label paint
  -> priority VOLUME_SET frame
  -> ESP32 media_player.volume_set on the configured test player
  -> subscribed HA volume_level callback
  -> VOLUME_RESULT frame
  -> S3 confirmation
```

Run 20 autonomous samples with:

```text
run_encoder_volume_sil_benchmark
```

The benchmark alternates between 0% and 2%, starts each sample only after the
preceding HA confirmation and ends at 0%. A single sample is available as
`run_encoder_volume_sil_probe`.

Implemented hot-path optimizations:

- the former fixed 150 ms encoder-to-network delay is removed;
- the volume label and arc are painted directly without rebuilding the rest
  of the media view;
- the S3 paints first and dispatches the UART frame immediately afterwards;
- volume has a dedicated sequence-numbered control frame rather than the
  generic dynamic-entity action payload;
- the ESP32 volume script uses `mode: restart`, so the newest value supersedes
  obsolete intermediate values;
- action diagnostic publications no longer precede `volume_set` on the same
  encrypted native-API connection;
- stale HA volume snapshots cannot overwrite an active optimistic value;
- HA confirmation completes telemetry without releasing the local accumulator;
- a 350 ms idle-release window accepts external HA changes only after the
  encoder has stopped, while every detent still renders and transmits
  immediately.

Final 20-sample run:

| Metric | Result |
| --- | ---: |
| Successful samples | 20 / 20 |
| Timeouts | 0 |
| Local label + arc render | 0.438 ms |
| UART bridge acceptance | 1.403 ms |
| Last HA/player confirmation | 97.241 ms |
| Last complete sample | 99.109 ms |
| Total p50 | 100.619 ms |
| Total p95 | 109.085 ms |
| Total maximum | 111.470 ms |
| S3 scheduler maximum gap | 5 ms |
| S3 / ESP32 UART protocol errors | 0 / 0 |
| Final player volume | 0% |

Three preceding clean runs measured p50 between 99.436 and 101.141 ms. The two
post-optimization confirmation runs measured p95 105.708 ms and 109.085 ms,
versus 110.474-127.302 ms before diagnostic publications were removed from the
control path. Local response is therefore sub-millisecond; the remaining
roughly 90-105 ms is the encrypted ESPHome API, Home Assistant, Music
Assistant/Sonos service handling and the player's confirmed state callback.
Rendering intentionally does not wait for it.
