# Firmware and integration 3.0.1-beta.5

Release description: `static-weather-overscan`

3.0.1-beta.5 removes the colored vertical columns introduced by the Beta.4
weather-image overscan. The same release standardizes the complete integration,
dual-ECU, website, HACS and Home Assistant rollout process for reuse.

## Customer-visible changes

- All 15 weather photographs are prepared at 368×368 before compilation and
  center-clipped to the 360×360 display.
- LVGL no longer scales or antialias-transforms the RGB565 weather image at
  runtime. Four static overscan pixels remain outside every panel edge.
- The thin exposed background seam remains covered without using the transform
  path that produced colored edge columns on hardware.
- Beta.4 media presentation behavior remains intact: the selected Home
  Assistant player is authoritative, media page and cover screensaver use the
  same committed title/artist cache, and reconnects rehydrate the presentation.

## Maintainer workflow

- `docs/release-runbook.md` now defines the coordinated release contract,
  preflight evidence, versioning, tests, all six firmware builds, immutable
  publication order, website verification, HACS install, logical device OTA,
  acceptance and rollback.
- `tools/qualify-release.sh` runs both supported Home Assistant test matrices in
  parallel, validates all six ESPHome profiles, compiles all managed and Factory
  profiles, assembles public artifacts and verifies their versions and hashes.
- The reusable Codex skill `passion-wave-release` encapsulates the workflow and
  provides a bounded HACS/Home Assistant rollout helper.

## Root cause

The original 360×360 photographs contained a circular motif tangent to the
left and right image boundaries. Rendering them at their exact source size
could expose a thin page-background seam. Beta.4 addressed that by asking LVGL
to scale each embedded RGB565 image to 102 percent at runtime. On the physical
S3 display, the transform generated invalid-looking colored vertical columns
at the overscan boundary.

Beta.5 performs the small enlargement offline in the source artifacts. ESPHome
encodes a normal 368×368 RGB565 descriptor; LVGL positions it centrally and the
display viewport clips four pixels on every side. No transformed pixels or
out-of-bounds interpolation are involved at runtime.

## Verification

- Home Assistant 2026.7.4 and 2026.8.2: 83 tests and four subtests pass per
  version.
- The weather regression contract requires 15 JPEG assets at exactly 368×368,
  centered rendering and no `scale` or `antialias` property on the widget.
- All six Factory and managed ESPHome configurations validate and compile with
  ESPHome 2026.7.0.
- Generated manifests advertise `3.0.1-beta.5` and contain the matching OTA
  MD5, immutable release URL and chip family.
- The four public artifacts match `release/public/SHA256SUMS`.

## Public artifact checksums

```text
fd1cd2744b81cb0f4e860bb41e41eb7804b8d14a7dd1d235bf5ac1da49bf10de  s3/passion-wave-rotaryknob-s3-3.0.1-beta.5.factory.bin
c4efebcf76cd8861d4b17433e7718153a7ab73a5b8292bf28479355b9005b0af  s3/passion-wave-rotaryknob-s3-3.0.1-beta.5.ota.bin
bfceafee369b9550a520fd27bea4fd8b17399bb9fedb9282f99fcb4f92c7ae65  esp32/passion-wave-rotaryknob-esp32-3.0.1-beta.5.factory.bin
b96bb6bebe3fdefec0049f450280a5c6916bcc6f088f871c1529686508fd8cf0  esp32/passion-wave-rotaryknob-esp32-3.0.1-beta.5.ota.bin
```

Managed S3 uses 52.8 percent RAM and 73.9 percent flash. Managed Bridge uses
40.3 percent RAM and 62.8 percent flash. The public Factory builds use 52.9 /
73.9 percent on S3 and 40.4 / 63.0 percent on Bridge respectively.

## Live acceptance on Timo and Marco

1. Install integration 3.0.1-beta.5 through HACS and wait for Home Assistant
   Core state `RUNNING` after restart.
2. Refresh each logical PassionWave firmware entity and require Beta.5 as the
   offered version.
3. Update one product at a time through the same versionless `update.install`
   call used by the UI.
4. Require Bridge then S3 installation, final `phase=complete`, both processors
   on 3.0.1-beta.5, both connected and no error.
5. Open the weather screensaver on both displays and inspect left, right, top
   and bottom edges. Neither white seams nor colored vertical columns may be
   visible.
6. Verify the selected player, runtime title/artist/cover and rendered title
   recover after both processor reboots without a manual integration reload.
