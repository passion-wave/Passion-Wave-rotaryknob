# Light mV Calibration

Some Zigbee rain and light sensors expose the brightness channel as a raw
millivolt-like value instead of a calibrated `lx` value. There is no reliable
universal lookup table for this conversion: the raw voltage depends on the
sensor element, resistor network, ADC reference, firmware scaling, lens,
mounting angle, dirt on the cover and the direction of the sun.

The included Home Assistant package therefore treats the result as an
estimated illuminance value. It keeps the raw value visible, maps it through
local calibration anchors and exposes a coarse daylight class that is more
stable for automations than the raw mV number.

## Package

Copy this file into Home Assistant:

```text
home_assistant/packages/light_mv_calibration.yaml
```

The package creates:

- `input_text.light_mv_source_entity`: raw source sensor entity.
- `input_text.light_mv_weather_entity`: weather entity used as calibration
  context.
- `input_boolean.light_mv_auto_calibration`: enables slow automatic anchor
  updates.
- four mV anchor inputs: dark, dim indoor, overcast daylight and direct sun.
- `sensor.light_raw_mv`: normalized raw value.
- `sensor.light_estimated_illuminance`: estimated `lx`.
- `sensor.light_solar_expected_illuminance`: weather/sun-context estimate.
- `sensor.light_daylight_class`: stable classes such as `night`,
  `overcast_daylight` and `direct_sun`.
- statistics sensors for 24 h minimum, 24 h maximum and 7 d maximum.

The default source is:

```text
sensor.outdoor_regenlichtsensor_illuminance_raw
```

Change `input_text.light_mv_source_entity` if your raw sensor has another
entity ID.

## Calibration Model

The first mapping uses four local anchors:

| Anchor | Meaning | Default target |
| --- | --- | --- |
| Dark reference | Night / covered sensor | about `0.2 lx` |
| Dim indoor reference | Low indoor light | about `100 lx` |
| Overcast daylight reference | Bright outdoor shade or overcast day | about `2000 lx` |
| Direct sun reference | Strong sunlight | about `50000 lx` |

Set the anchors by observing the raw mV value in real situations:

1. Cover the sensor or wait for a dark night and set `Light mV dark reference`.
2. Use a dim indoor or shaded threshold and set `Light mV dim indoor reference`.
3. On an overcast day, set `Light mV overcast daylight reference`.
4. In direct sun near noon, set `Light mV direct sun reference`.

For automation decisions, prefer `sensor.light_daylight_class` or broad ranges
from `sensor.light_estimated_illuminance`. Treat the numeric lux value as a
local estimate, not as a certified measurement.

## Automatic Recalibration

The package includes slow, conservative recalibration:

- At night, the 24 h minimum slowly updates the dark anchor.
- Around local noon, sunny or partly cloudy days slowly update the direct-sun
  anchor.
- During cloudy, rainy or foggy daylight, the current raw value slowly updates
  the overcast-daylight anchor.

This can compensate for seasonal sun angle, sensor aging and dirt. It cannot
create absolute lux accuracy without a real reference sensor. If the sensor is
mounted where lamps, shadows or reflections dominate the reading, disable
`Light mV auto calibration` and set the anchors manually.

## Useful Reference Classes

Use these broad bands when designing automations:

| Estimated lux | Class |
| --- | --- |
| `< 1 lx` | night |
| `1..10 lx` | very dark |
| `10..100 lx` | dim indoor |
| `100..500 lx` | indoor |
| `500..2000 lx` | low daylight |
| `2000..10000 lx` | overcast daylight |
| `10000..30000 lx` | bright daylight |
| `> 30000 lx` | direct sun |

These are intentionally broad because weather, window orientation and the
sensor optics have a larger effect than the arithmetic conversion.
