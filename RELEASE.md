# Version 2.1.0

Release description: `reliable-onboarding,responsiveness`

## Scope

Version 2.1.0 turns the dual-processor architecture into a complete public
two-stage release:

- Home Assistant discovers two explicit nodes, `PassionWave Rotaryknob` and
  `PassionWave Rotaryknob Bridge`;
- chip-specific manifests require a clean erase, preventing stale private
  names, Wi-Fi state and former API credentials from surviving a factory flash;
- both public profiles expose a credential-free first-adoption API, while
  private development wrappers retain encrypted API and password-protected OTA;
- the S3 remains awake until Home Assistant has connected once, so the longer
  two-chip installation cannot hide it before discovery;
- manifests are generated from the same `VERSION` and build command as the
  factory binaries and are imported downstream together;
- the radar asset path now follows its independent ESP32 capability instead of
  being blocked by unrelated media/light target differences;
- radar and floorplan diagnostics no longer overwrite each other;
- ESP32-S3 owns touch, EC1 encoder, LVGL, haptics and immediate optimistic UI;
- ESP32 owns EC2, Home Assistant communication and network/library offload;
- the inter-MCU UART link uses framed, prioritized and acknowledged messages;
- both processors retain independent OTA and serial recovery paths;
- credential-free factory profiles support an ungeflashed retail device;
- private test wrappers remain separate from public release cores.
- all 15 Home Assistant weather conditions have dedicated, locally compiled
  360 x 360 screensaver images on the S3, with no runtime image download and a
  deterministic `partlycloudy` fallback.
- the screensaver starts at 100% display brightness, fades natively and
  continuously to 10% over a persistent Home Assistant configurable duration
  (default five minutes), and restores the 70% UI brightness immediately when
  closed without adding periodic scheduler load.
- encoder movement on the active screensaver restores 100% brightness for two
  seconds after the final pulse and then restarts the configured native fade;
  the input is consumed before it can trigger an underlying UI control.
- Home Assistant exposes clearly separated native configuration numbers for
  the screensaver start delay and the 100-to-10% dimming duration.

## Canonical structure

- `esphome/*-core.yaml`: credential-free application sources.
- `esphome/dual-mcu-test-*.yaml`: private development wrappers.
- `esphome/factory-*.yaml`: public retail build entry points.
- `home_assistant/`: Home Assistant Apps/blueprints and optional packages.
- `home-assistant/`: advanced legacy utilities pending final directory merge.
- `docs/`: architecture, migration, installation and acceptance evidence.
- `tools/`: build, flash, diagnostics and release scripts.
- `release/public/`: generated S3/ESP32 factory artifacts and checksums.

## Downstream contract

`Passion-Wave-web` must publish the two files from `release/public/` without
rebuilding or renaming them and must keep one chip family per guided installer
stage. `Passion-Wave-control` records the release order and external launch
gates.

## Version history

Version 2.1.0 is released from `main`. Version 2.0.0 remains the immutable
architecture baseline at tag `v2.0.0`; `stable/1.2.0` remains the legacy
single-MCU rollback point.

- `main`: active Version 2.1 production line.
- `feature/next`: retained as Version 2.0 integration history.
- `stable/1.2.0`: unchanged rollback point for Version 1.2.0.

## Verified Version 2.1 public artifacts

On 2026-07-26 both credential-free factory profiles resolved and compiled with
ESPHome 2026.7.0. The S3 image uses 71.7% of its app partition and 57.5% of
available runtime RAM; the ESP32 image uses 59.6% of its app partition and
43.4% of runtime RAM. Both manifests expose one chip family, version `2.1.0`,
the intended PassionWave name, clean erase and a 120-second Improv wait.

```text
3ff5c25b9a99d1ae6dbb4722c07312acc30a1c44cb50112eefcf6ab77e48355b  s3/passion-wave-rotaryknob-s3.factory.bin
ea04ec704adf7951b292a57d1091633629d500c2cb0562d64bb7bf3b7cdab392  esp32/passion-wave-rotaryknob-esp32.factory.bin
```

## Previous verified maintenance baseline

The immutable `v2.0.0` tag remains the release anchor. `main` additionally
contains Version 2.0 maintenance fixes and is the source for current builds.
On 2026-07-25 both private test processors were rebuilt with ESPHome 2026.7.0,
flashed independently by OTA and read back through the native ESPHome API:

- S3 project `passion-wave.rotaryknob-test-s3`, version `2.0.0`;
- ESP32 project `passion-wave.rotaryknob-test-esp32`, version `2.0.0`;
- shared native Music Assistant test target on both processors;
- shared four-light target snapshot;
- runtime status `ESP32 HA-Bridge aktiv`.
- Music Assistant playlist paging verified with 140/140 entries on both
  processors, including automatic continuation beyond the retained
  40-entry bootstrap; inter-MCU protocol errors remained zero.
- weather screensaver maintenance build flashed to the S3 test device; the
  encrypted API handshake completed in 136 ms,
  inter-MCU protocol errors remained zero and steady scheduler windows were
  normally 13–18 ms.

The corresponding credential-free factory artifacts were regenerated from the
same Version 2.0 cores:

```text
d2f1c68323014953bf5bd4d4dac7786508417792447a49fe92d3275957965869  s3/passion-wave-rotaryknob-s3.factory.bin
89f2c1a68a97abe2c2c6f2a86c3be8019f0fe7aa1e9d7d23a12cf8f9b0f5fe57  esp32/passion-wave-rotaryknob-esp32.factory.bin
```
