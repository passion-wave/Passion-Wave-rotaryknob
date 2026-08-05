# Rotary Recognition

The JC3636K518C knob is not a quadrature encoder. It provides one active-low
pulse output per direction, duplicated as EC1 and EC2 for the two processors.
One falling edge represents one mechanical detent; the wire identifies the
direction.

## Hardware mapping and authority

| Path | Pin | Signal | Direction | Step | Role |
| --- | --- | --- | --- | --- | --- |
| EC1 / ESP32-S3 | `GPIO7` | `EC1_B` | counter-clockwise / left | `-1` | authoritative UI input |
| EC1 / ESP32-S3 | `GPIO8` | `EC1_A` | clockwise / right | `+1` | authoritative UI input |
| EC2 / ESP32 | `GPIO22` | `EC2_B` | counter-clockwise / left | `-1` | diagnostic only |
| EC2 / ESP32 | `GPIO19` | `EC2_A` | clockwise / right | `+1` | diagnostic only |

The measured EC1 log produced exclusively unit increments, whereas EC2 had
large jumps. EC1 therefore remains authoritative. Never add EC1 and EC2: both
describe the same physical movement and would duplicate detents.

## Why the 1.2.0 reader became sluggish

The original implementation represented GPIO7 and GPIO8 as ESPHome GPIO binary
sensors. Their `on_press` callbacks modified one shared `knob_delta`, and a
20 ms application interval read and cleared it.

That design had three loss mechanisms under fast input or S3 load:

- pulse recognition depended on the application loop observing the GPIO
  component's latest state;
- a complete short pulse could occur while LVGL, image decode or networking
  occupied that loop;
- `knob_delta` was cleared before sleep and page checks, permanently discarding
  already detected movement.

Polling that design faster would reduce average latency but would not make
acquisition independent of application-loop stalls.

## Implemented PCNT acquisition

[`ec1_pcnt_encoder.h`](../esphome/ec1_pcnt_encoder.h) configures two independent
ESP32-S3 hardware pulse-counter units:

- GPIO7 and GPIO8 each own one PCNT unit;
- both active-low inputs explicitly retain their internal pull-ups after the
  PCNT GPIO matrix claims them;
- only the falling edge increments the corresponding counter;
- a 10 microsecond hardware glitch filter rejects very short electrical
  spikes;
- high and low watch points enable the ESP-IDF overflow accumulator;
- runtime reads never clear the hardware counters.

Using separate left and right counters prevents opposite pulses from hiding
acquisition statistics. The UI obtains a batch every 10 ms and calculates:

```cpp
const auto batch = ec1_pcnt::encoder.take();
const int steps = batch.signed_steps();
```

PCNT keeps counting while the application loop is busy. A delayed UI cycle
therefore receives the complete accumulated batch instead of losing pulses.
Because EC1 provides a separate line per direction, a batch in which both
lines counted pulses has no reliable direction. Such common-mode batches are
retained in the raw diagnostics but yield zero accepted steps. They cannot
update UI activity, restore a dimmed display, wake a sleeping display or boost
the weather screensaver.

The existing page-specific logic consumes the same signed `steps` value, so
all 1.2.0 behavior remains intact:

- page 1: brightness or scene selection;
- pages 2 and 6: volume or media selection;
- page 11: timer adjustment;
- page 12: alarm hour/minute adjustment.

Haptics still run only when the active page consumes a rotary action.

## Sleep and reporting behavior

Only an unambiguous directional batch updates UI activity and restores an
externally powered, dimmed display. The first valid batch received during full
display sleep wakes the display and is not applied to a setting; subsequent
detents operate normally. This validation adds no debounce or wait to a valid
detent.

Home Assistant diagnostics are deliberately decoupled from the realtime path
and published from the low-priority diagnostic window:

- `EC1 Encoder Ready`;
- `EC1 Encoder Net Count`;
- `EC1 Encoder Left Pulses` and `EC1 Encoder Right Pulses`;
- `EC1 Encoder Rejected Common-mode Batches`;
- `EC1 Encoder Read Errors`;
- `EC1 Encoder Maximum Batch`.

`Net Count` contains only accepted directional input. The left and right raw
counters still expose electrical activity, while `Rejected Common-mode
Batches` proves how many ambiguous acquisitions were kept away from the UI.

The dual-MCU test forwards a 10 Hz EC1 snapshot over UART for comparison with
EC2. Network publishing and UART transmission never occur in an encoder ISR.

## Verification

Build the S3 profile and then test on the dedicated test device:

```sh
./tools/config.sh esphome/managed-test-s3.yaml
./tools/build.sh esphome/managed-test-s3.yaml
```

Acceptance criteria:

- `EC1 Encoder Ready` is on and read errors remain zero;
- each slow detent changes exactly one directional counter by one;
- direction is correct on every rotary-enabled page;
- fast spins produce the full expected movement without a delayed phantom
  burst;
- while idle, raw counters may expose common-mode activity, but accepted net
  count and the display state do not change;
- at 10% screensaver brightness, rejected common-mode batches never produce a
  short 100% brightness flash;
- a sleeping display wakes on the first detent and responds from the next;
- EC2 mismatch is recorded but never changes UI behavior.

The current processor split and scheduling rules are defined in
[`dual-mcu-ha-bridge.md`](dual-mcu-ha-bridge.md); physical regression steps are
in [`stage1-responsiveness-test-catalog.md`](stage1-responsiveness-test-catalog.md).
