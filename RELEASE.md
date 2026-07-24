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
