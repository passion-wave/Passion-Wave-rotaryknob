# Firmware and integration 3.0.1-beta.6

Release description: `fullscreen-cover-overscan`

3.0.1-beta.6 removes the exposed page-background strips at the left and right
edges of the fullscreen cover view. It keeps the Beta.5 static weather-image
overscan and the Beta.4 atomic title, artist and cover presentation intact.

## Customer-visible changes

- Fullscreen covers fill the 360×360 display with a four-pixel overscan on all
  edges.
- The S3 decodes directly to a 368×368 RGB565 surface and LVGL renders it at
  −4/−4 without scaling or antialias transformation.
- Music Assistant cover proxy requests use its supported 512-pixel source;
  the separate 124×124 media-page image remains unchanged.
- Media page and cover screensaver continue to read the same committed title,
  artist and cover URL and invalidate the previous decoded cover on a new
  presentation.

## Root cause

The fullscreen `media_cover_image` was still configured as 256×256 and its
widget was placed at `x=52`, `y=52`. That geometry covers only the centered
256-pixel square of a 360×360 panel, leaving 52 pixels of page background on
each side. The round visible area reduced those bands to the reported narrow
left and right strips, but they were not an image-download or clipping defect.
Beta.5 only changed the embedded weather artwork, so it could not affect this
independent online-cover widget.

Beta.6 uses the same static-overscan principle for the cover. Arbitrary Music
Assistant proxy sizes such as 368 and 384 return HTTP 400, while 512 is a
supported exact source size. The Bridge therefore requests 512, streams that
compressed image through the acknowledged UART asset channel, and the S3
decodes it directly to its final 368×368 render surface. Position −4/−4 lets
the panel viewport center-clip four real cover pixels on every edge.

## Verification

- Home Assistant 2026.7.4 and 2026.8.2: 84 tests and four subtests pass per
  version.
- The regression contract requires a 368×368 fullscreen decoded image,
  widget position −4/−4, proxy source size 512 and no fullscreen `scale` or
  `antialias` property.
- Generated ESPHome C++ must construct `media_cover_image` as 368×368 and set
  both widget coordinates to −4.
- All six Factory and managed ESPHome configurations validate and compile with
  ESPHome 2026.7.0.
- Generated manifests advertise `3.0.1-beta.6` and all four public artifacts
  match `release/public/SHA256SUMS`.
- The candidate builder now fixes ESPHome build metadata to the commit epoch,
  proves 4/4 bit-identical clean builds, emits dependency-complete CycloneDX
  provenance and fault-tests atomic promotion.

## Public artifact checksums

```text
9395201724c6892974c14b1150aa6db153d2ff8d9b9050cdd0650d05b1c4ef23  s3/passion-wave-rotaryknob-s3-3.0.1-beta.6.factory.bin
c5b772d3d69aeaffc47c2adba7df54fbfec7c681b428e35219a77815d458e61b  s3/passion-wave-rotaryknob-s3-3.0.1-beta.6.ota.bin
a4b8743a1b628a10f1f54f037c9d2957d95d4c629bfd9db4b04e54aae274ab3e  esp32/passion-wave-rotaryknob-esp32-3.0.1-beta.6.factory.bin
b3fe3d9b38ce903595b73b4f27df26bfecebb9031c0c1c7fd98ade212048876d  esp32/passion-wave-rotaryknob-esp32-3.0.1-beta.6.ota.bin
```

Managed S3 uses 52.8 percent RAM and 73.9 percent flash. Managed Bridge uses
40.3 percent RAM and 62.8 percent flash. The public Factory builds use 52.9 /
73.9 percent on S3 and 40.4 / 63.0 percent on Bridge respectively.

## Live acceptance on Timo and Marco

1. Install integration 3.0.1-beta.6 through HACS and wait for Home Assistant
   Core state `RUNNING` after restart.
2. Refresh each logical PassionWave firmware entity and require Beta.6 as the
   offered version.
3. Update one product at a time through the same versionless `update.install`
   call used by the Home Assistant UI.
4. Require Bridge then S3 installation, final `phase=complete`, both processors
   on 3.0.1-beta.6, both connected and no error.
5. Open the cover screensaver with at least five bright and dark covers on both
   displays. Left, right, top and bottom must show neither page background,
   white seams nor colored columns.
6. During those title changes, media page and cover screensaver must display
   the same current title, artist and cover.

Remote live result on 2026-08-20: steps 1–4 passed for Timo and Marco. HACS
installed integration 3.0.1-beta.6 and Home Assistant reached `RUNNING` after
restart. The single logical update transaction updated Timo first and Marco
second; both ended `off` with `phase=complete`, Bridge and S3 on
3.0.1-beta.6, both connections active and `last_error=null`.

After both processor reboots, Timo's player, runtime title and rendered title
all reported `He's a Pirate`; runtime artist was `Klaus Badelt` and the runtime
cover URL equalled the selected player's current 512-pixel Music Assistant
proxy URL. Marco's selected player and rendered title both reported
`Kapitel 03: Spur der Tresorknacker - Folge 102`; artist was
`Die drei ??? Kids`, and UI plus valid clock were ready after 1.951 seconds.
Marco's optional detailed runtime diagnostics remained disabled and therefore
`unavailable`, as expected. Steps 5–6 still require direct observation on the
two physical displays and are not claimed from remote diagnostics.
