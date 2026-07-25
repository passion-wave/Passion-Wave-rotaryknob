# Weather screensaver source collage

`weather-condition-collage-source.png` is the original user-provided visual
reference for a future photographic weather screensaver.

Technical properties:

- 1254 x 1254 pixels;
- RGB PNG without alpha;
- three by three circular motifs with white gutters;
- SHA-256:
  `ba3f8ca1326ef007e80532cb4bca1f489833d78e72de928992568fab192b6408`.

The collage is intentionally stored as a source asset. It is not currently
compiled into the firmware: the existing screensaver is rendered from LVGL
objects, and the complete collage would waste flash and runtime memory. Before
integration, each approved motif must be cropped, resized and converted into a
device-appropriate asset.

## Coverage audit

Positions use `R<row>C<column>`, counted from the upper left.

| Firmware condition | Proposed motif | Coverage |
|---|---:|---|
| `clear-night` | — | missing: a calm, clear night sky is required |
| `cloudy` | R1C3 | direct |
| `exceptional` | R2C3 | partial: thunderstorm is not a universal exceptional condition |
| `fog` | R3C1 or R3C3 | direct; the collage contains two similar fog motifs |
| `hail` | — | missing: rain does not communicate hail |
| `lightning` | R2C3 | direct |
| `lightning-rainy` | R2C3 | partial: lightning is clear, rain is not |
| `partlycloudy` | R1C2 | direct |
| `pouring` | R2C2 | direct |
| `rainy` | R2C1 | direct |
| `snowy` | R3C2 | direct |
| `snowy-rainy` | — | missing: mixed snow and rain is required |
| `sunny` | R1C1 | direct |
| `windy` | — | missing: no visible wind cue |
| `windy-variant` | — | missing: clouds are present, but wind is not communicated |
| unknown/fallback | — | a neutral fallback motif is required |

The nine tiles therefore provide eight clearly distinct weather classes; the
two fog tiles are visually redundant. The collage cannot represent all 15
supported Home Assistant conditions unambiguously.

## Required completion set

For complete screensaver coverage, add at least these five motifs in the same
color treatment, exposure, circular crop and camera style:

1. clear night;
2. hail;
3. mixed snow and rain;
4. wind without dominant cloud cover;
5. wind with cloud cover.

An additional neutral fallback and a more general severe-weather motif are
recommended. Distribution rights and final image provenance must be confirmed
before these assets are shipped in public factory firmware.
