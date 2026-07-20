# Rotary Recognition

The JC3636K518C knob used by Passion Wave Rotaryknob is not handled as a
classic quadrature encoder. Practical testing against the guition
JC3636K718C implementation showed that the hardware emits one clean active-low
pulse per detent, while the direction is encoded by the pin that pulses.

## Hardware Mapping

| Pin | Direction | Step |
| --- | --- | --- |
| `GPIO7` | counter-clockwise / left | `-1` |
| `GPIO8` | clockwise / right | `+1` |

Both pins are configured as internal GPIO binary sensors with pull-ups and
`inverted: true`. Every `on_press` updates the shared `knob_delta` counter.

## Current Implementation

The firmware uses this direct pulse model:

```yaml
binary_sensor:
  - platform: gpio
    id: knob_left
    internal: true
    pin:
      number: GPIO7
      inverted: true
      mode:
        input: true
        pullup: true
    on_press:
      - lambda: |-
          id(knob_delta)--;
          id(ui_last_activity_ms) = millis();

  - platform: gpio
    id: knob_right
    internal: true
    pin:
      number: GPIO8
      inverted: true
      mode:
        input: true
        pullup: true
    on_press:
      - lambda: |-
          id(knob_delta)++;
          id(ui_last_activity_ms) = millis();
```

The 20 ms interval consumes the accumulated delta and keeps the existing
page-specific action logic unchanged:

```cpp
int steps = id(knob_delta);
id(knob_delta) = 0;
if (id(display_sleeping)) {
  return;
}
if (steps == 0) {
  return;
}
```

All pages continue to use the same `steps` variable:

- Page 1: brightness or scene selection.
- Page 2 and 6: volume or media selection.
- Page 11: timer adjustment.
- Page 12: alarm hour/minute adjustment.

Rotary haptics are still only played when the current page consumes the rotary
step.

## Removed Legacy Decoder

The older implementation used a custom ISR accumulation decoder in
`encoder_pulse_decoder.h` with pulse balancing, thresholds and burst
finalization. That model treated the knob like a noisy multi-pulse encoder and
introduced latency, swallowed steps, duplicate steps and occasional direction
errors.

The legacy header is intentionally no longer part of the ESPHome include list.
The installation structure must not reference it.

## Sleep And Dimming Behavior

When the display is fully sleeping on battery, rotary input is ignored after
the delta is consumed. This prevents a knob bump from waking a battery-powered
device.

When the device is externally powered and only dimmed for display protection,
touch or rotary activity restores the normal backlight level without changing
the page-specific rotary semantics.

## Verification

Run:

```sh
./tools/config.sh esphome/passion-wave-rotaryknob.yaml
./tools/build.sh esphome/passion-wave-rotaryknob.yaml
```

Then flash and verify on device:

- One detent left creates exactly one negative step.
- One detent right creates exactly one positive step.
- Direction is correct on the light page.
- No phantom steps happen while idle.
- Fast rotation does not create delayed catch-up bursts.
- Page behavior remains correct on pages 1, 2, 6, 11 and 12.

If a future hardware revision loses pulses under heavy LVGL load, the fallback
is an interrupt-based one-pulse-per-step decoder with no pulse thresholding and
no burst finalization. Direction should still be determined only by whether
`GPIO7` or `GPIO8` pulsed.
