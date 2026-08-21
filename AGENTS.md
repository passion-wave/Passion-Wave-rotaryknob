# RotaryKnob agent and documentation contract

This file is the short router for work in this repository. Read only the row
that matches the task, then the linked canonical document. Cross-repository
candidate creation starts in `Passion-Wave-control/tools/release`; do not
invent a second release sequence here.

## Minimal task routing

| Change | Read first | Required local check |
| --- | --- | --- |
| Home Assistant integration | `docs/dual-mcu-ha-bridge.md`, relevant tests | `tools/fast-check.sh --scope integration` |
| S3 UI, touch, EC1 or images | `docs/ui-next-framework.md`, relevant feature doc | `tools/fast-check.sh --scope s3` |
| Bridge, EC2, UART or network assets | `docs/dual-mcu-ha-bridge.md`, `docs/debugging.md` | `tools/fast-check.sh --scope bridge` |
| Factory/security/onboarding | `docs/api-security-lifecycle.md`, `docs/installation.md` | `tools/fast-check.sh --scope all` |
| Candidate build | `docs/build-pipeline.md` | run from Control: `tools/release build ...` |
| Atomicity/failure injection | `docs/build-pipeline.md` | `tools/test-release-atomicity.sh` |
| Publish/HACS/device OTA | `docs/release-runbook.md` | use an immutable qualified receipt |
| Physical defect or acceptance | `docs/known-issues.md`, test catalog | record observed, remote and automated evidence separately |
| Documentation only | this file plus the target document | Control `tools/release check` with the current contract channel |

## Invariants and generated files

- One product is always one S3 plus one classic ESP32; both ship at one SemVer.
- `VERSION` is the runtime SemVer. The integration manifest uses its PEP 440
  mapping (`alpha→a`, `beta→b`, `rc→rc`).
- Never edit generated build trees (`esphome/.esphome`, `.esphome_cache`,
  `.release-pipeline`) or derived stable manifests by hand.
- `release/public/` is promoted only by `tools/build-public-release.sh` after
  hashes and both manifests pass. Historical immutable artifacts are retained.
- No real Wi-Fi, API, OTA, Home Assistant or customer identifiers may enter
  tracked files. `esphome/secrets.yaml` is forbidden.
- A configured endpoint or remote entity is not physical visual evidence.
- Full logs belong below `.release-pipeline`; agent handoff uses only
  `release-status.json` and `SUMMARY.md` from the Control repository.

## Documentation ownership

Statuses: `evergreen` contains no current version, `current` is the one mutable
release/issue surface, `historical` is frozen evidence, and `generated` is
derived by tooling. Every tracked Markdown object appears exactly once below.

<!-- docs-index:start -->
| Path | Status | Authority and read trigger |
| --- | --- | --- |
| `AGENTS.md` | `evergreen` | Agent routing, invariants and complete document inventory. |
| `README.md` | `evergreen` | Product and repository entry; read when changing supported architecture. |
| `RELEASE.md` | `current` | Current human release delta and acceptance evidence. |
| `assets/screensaver/README.md` | `evergreen` | Weather artwork provenance and condition mapping. |
| `docs/api-security-lifecycle.md` | `evergreen` | Factory-to-managed credentials, provisioning and OTA security. |
| `docs/archive/known-issues-history.md` | `historical` | Frozen resolved issues, superseded Beta evidence and old test windows. |
| `docs/build-pipeline.md` | `evergreen` | Local gates, stage policy, receipts, cache and failure recovery. |
| `docs/configuration.md` | `evergreen` | Runtime configuration model and entity ownership. |
| `docs/customer-processes.md` | `evergreen` | Customer purchase, setup, update, support and reset journey. |
| `docs/customer-product-architecture.md` | `evergreen` | Product boundary, identity and two-chip delivery model. |
| `docs/debugging.md` | `evergreen` | Serial/API logs and fault isolation. |
| `docs/dual-mcu-ha-bridge.md` | `evergreen` | S3/Bridge/HA ownership, UART protocol and media signal chains. |
| `docs/end-to-end-latency-benchmark.md` | `historical` | Frozen performance method and dated measurements. |
| `docs/home-assistant-floorplan-renderer.md` | `evergreen` | Optional floorplan renderer. |
| `docs/installation.md` | `evergreen` | Browser installation, maintainer flashing and recovery. |
| `docs/known-issues.md` | `current` | Active issues, live observations and acceptance ledger. |
| `docs/light-mv-calibration.md` | `evergreen` | Optional light sensor calibration. |
| `docs/managed-deployment.md` | `evergreen` | Managed profiles, OTA topology and deployment rules. |
| `docs/power-optimization.md` | `evergreen` | Power states, measurement and responsiveness limits. |
| `docs/radar-floorplan-data-flow.md` | `evergreen` | Network-image source and transfer contracts. |
| `docs/release-runbook.md` | `evergreen` | Publication, HACS, serial device rollout and rollback. |
| `docs/rotary-recognition.md` | `evergreen` | Encoder recognition, filtering and counters. |
| `docs/stage1-responsiveness-test-catalog.md` | `historical` | Frozen full functional and endurance catalog. |
| `docs/ui-next-framework.md` | `evergreen` | LVGL pages, input, popups and rendering ownership. |
| `docs/unflashed-customer-onboarding.md` | `evergreen` | Clean-device two-stage browser onboarding. |
| `docs/ux-assurance-report.md` | `historical` | Frozen static UI audit and remaining physical checks. |
<!-- docs-index:end -->

## Change handoff

Report the affected processor/integration, exact checks run, receipt or input
fingerprint, and any unverified manual gate. Do not paste complete build logs
into chat or Markdown; provide the short failing gate and its log path.
