# Weather screensaver collage v1

`weather-state-collage-v1.png` is the original 3 x 3 design collage supplied
on 2026-07-25. It is a design source, not yet a runtime sprite sheet.

The firmware accepts all 15 Home Assistant weather conditions defined in
`esphome/dual_mcu_link.h`. The collage contains eight visually distinct
condition archetypes plus a second fog variation:

| Grid position | Motif | Exact Home Assistant condition |
| --- | --- | --- |
| row 1, column 1 | sun | `sunny` |
| row 1, column 2 | sun and clouds | `partlycloudy` |
| row 1, column 3 | overcast sky | `cloudy` |
| row 2, column 1 | light rain | `rainy` |
| row 2, column 2 | heavy rain | `pouring` |
| row 2, column 3 | lightning | `lightning` |
| row 3, column 1 | dense forest fog | `fog` |
| row 3, column 2 | snow | `snowy` |
| row 3, column 3 | light field fog | optional second `fog` variant |

## Coverage of all firmware conditions

| Home Assistant condition | Collage mapping | Assessment |
| --- | --- | --- |
| `clear-night` | none | missing; a night motif is required |
| `cloudy` | row 1, column 3 | exact |
| `exceptional` | row 2, column 3 | fallback only; exceptional is not always a thunderstorm |
| `fog` | row 3, column 1 or 3 | exact |
| `hail` | row 2, column 1 | fallback only; hail is not visible |
| `lightning` | row 2, column 3 | exact |
| `lightning-rainy` | row 2, column 3 | fallback only; rain is not clearly visible |
| `partlycloudy` | row 1, column 2 | exact |
| `pouring` | row 2, column 2 | exact |
| `rainy` | row 2, column 1 | exact |
| `snowy` | row 3, column 2 | exact |
| `snowy-rainy` | row 3, column 2 | fallback only; sleet is not visible |
| `sunny` | row 1, column 1 | exact |
| `windy` | row 1, column 1 | fallback only; wind is not visible |
| `windy-variant` | row 1, column 3 | fallback only; wind is not visible |

Conclusion: the collage can provide a fallback for every condition, but it
cannot represent all 15 conditions unambiguously. A production-complete set
still needs dedicated motifs for `clear-night`, `exceptional`, `hail`,
`lightning-rainy`, `snowy-rainy`, `windy`, and `windy-variant`.

Before firmware integration, export individual display-sized images without
the white collage background, apply a dark readability treatment for clock
and status text, and define a memory-safe preload/cache strategy. Until then,
the existing vector-based weather screensaver remains the runtime source.
