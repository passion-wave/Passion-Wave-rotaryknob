# Version 2.0.0

Release description: `responsiveness,nextUI`

## Scope

Version 2.0.0 promotes the dual-processor architecture and NextUI from the
migration branch to the coordinated product release:

- ESP32-S3 owns touch, EC1 encoder, LVGL, haptics and immediate optimistic UI;
- ESP32 owns EC2, Home Assistant communication and network/library offload;
- the inter-MCU UART link uses framed, prioritized and acknowledged messages;
- both processors retain independent OTA and serial recovery paths;
- credential-free factory profiles support an ungeflashed retail device;
- private test wrappers remain separate from public release cores.

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

## Branch integration

The Version 2.0 implementation was developed on `feature/next` and
fast-forwarded into `main` on 2026-07-25. The immutable release tag `v2.0.0`
points to commit `6ce110b` with description `responsiveness,nextUI`.

- `main`: active Version 2.0 production line.
- `feature/next`: retained at the same release commit for traceability.
- `stable/1.2.0`: unchanged rollback point for Version 1.2.0.

The integration introduced no merge commit and no conflict resolution because
`main` was a direct ancestor of `feature/next`.

## Verified maintenance baseline

The immutable `v2.0.0` tag remains the release anchor. `main` additionally
contains Version 2.0 maintenance fixes and is the source for current builds.
On 2026-07-25 both private test processors were rebuilt with ESPHome 2026.7.0,
flashed independently by OTA and read back through the native ESPHome API:

- S3 project `passion-wave.rotaryknob-test-s3`, version `2.0.0`;
- ESP32 project `passion-wave.rotaryknob-test-esp32`, version `2.0.0`;
- shared native Music Assistant target `media_player.move_2`;
- shared four-light target snapshot;
- runtime status `ESP32 HA-Bridge aktiv`.

The corresponding credential-free factory artifacts were regenerated from the
same Version 2.0 cores:

```text
fdbece5c268eb5f83acc3dafb865fdc954575662a6fc479071942c046ce9b87a  s3/passion-wave-rotaryknob-s3.factory.bin
3c5db0c897d0afbe6645faa82d460b95714b516767bed18e5417b49ad1162eb5  esp32/passion-wave-rotaryknob-esp32.factory.bin
```
