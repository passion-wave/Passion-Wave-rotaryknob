# Passion Wave documentation map

This file is the maintained index for repository documentation. Read the
smallest relevant set before changing firmware, Home Assistant integration,
release assets or customer instructions. Do not reintroduce separate migration
logs for completed architecture work; Git preserves that history.

## Canonical project documents

- `AGENTS.md` — Maintained documentation index and repository documentation
  rules.
- `README.md` — Product overview, current coordinated version, architecture,
  setup summary and primary documentation entrypoints.
- `RELEASE.md` — Exact release status, customer-visible changes, verification
  results and immutable public artifact checksums.
- `docs/known-issues.md` — Current live-device results, open defects, physical
  acceptance matrix and resolved findings. Update this after every hardware
  verification session.
- `docs/installation.md` — Complete public browser installation plus manual
  maintainer build, flash and Home Assistant setup.
- `docs/configuration.md` — Runtime settings, PassionWave Config Flow, media,
  weather, display protection and privacy defaults.
- `docs/debugging.md` — Log collection, serial/API diagnostics and focused
  troubleshooting commands.
- `docs/power-optimization.md` — Current dual-MCU power behavior, measurement
  method, prioritized runtime optimizations and responsiveness acceptance gates.

## Architecture and deployment

- `docs/customer-product-architecture.md` — Customer-facing product boundary,
  two-chip installation model, identity, security and delivery expectations.
- `docs/dual-mcu-ha-bridge.md` — Current S3/Bridge ownership, UART protocol,
  state/command paths, recovery behavior and qualification gate.
- `docs/managed-deployment.md` — Four managed endpoint profiles, safe flashing,
  Home Assistant registration, acceptance and OTA recovery.
- `docs/api-security-lifecycle.md` — Factory-to-managed API encryption,
  provisioning window, OTA authentication and credential rules.
- `docs/ui-next-framework.md` — Current UI composition, page ownership,
  navigation, popups, rendering and display behavior.

## Customer and factory flows

- `docs/customer-processes.md` — Concise customer journey for purchase,
  installation, onboarding, updates, support and reset.
- `docs/unflashed-customer-onboarding.md` — Detailed clean-device two-stage
  browser onboarding and acceptance for unflashed sales hardware.

## Feature documentation

- `docs/radar-floorplan-data-flow.md` — End-to-end radar and floorplan asset
  transport, Home Assistant sources and diagnostic checkpoints.
- `docs/home-assistant-floorplan-renderer.md` — Optional Pyscript renderer for
  producing the live 360×360 floorplan PNG.
- `docs/light-mv-calibration.md` — Optional Home Assistant package for turning
  raw light-sensor millivolts into estimated illuminance.
- `docs/rotary-recognition.md` — EC1 encoder recognition, filtering, direction,
  counters and physical validation.
- `assets/screensaver/README.md` — Weather-screen source provenance, all 15
  condition mappings, checksums and runtime behavior.

## Verification documents

- `docs/stage1-responsiveness-test-catalog.md` — Detailed functional,
  navigation, encoder, media, light, weather, recovery and endurance tests.
- `docs/end-to-end-latency-benchmark.md` — Benchmark method, diagnostic probes,
  historical measurements and limits; old measurements are not current proof.
- `docs/ux-assurance-report.md` — Static 360×360 touch-target, page, rotary and
  UI layout audit plus remaining physical UX checks.

## Documentation maintenance rules

- `VERSION`, firmware project versions, integration version, manifests,
  `README.md` and `RELEASE.md` must describe the same coordinated release.
- One physical RotaryKnob always means one S3 plus one classic ESP32. Never
  report a profile or Home Assistant entry as a physically verified endpoint
  without live evidence.
- Record observed hardware behavior in `docs/known-issues.md`; keep exact test
  steps and expected results in the acceptance matrix or test catalog.
- Keep real Wi-Fi, API, OTA, Home Assistant and customer identifiers out of
  tracked Markdown and YAML. Use generic endpoint names and placeholders.
- When removing or renaming a document, update links in this repository and in
  `Passion-Wave-control` before considering the change complete.
