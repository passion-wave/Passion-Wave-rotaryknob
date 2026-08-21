# Firmware and integration 3.0.1-beta.11

Release summary: Deterministic web manifests and customer update acceptance

## Repository scope

- Role: S3, Bridge and Home Assistant implementation.
- Runtime/channel metadata: `VERSION` and the Control release contract.
- OIDs, toolchain digests, gate durations and payload hashes: generated release receipt.

## Automated evidence

Run the channel pipeline and attach the resulting receipt. Do not paste or
manually transcribe checksums; promotion verifies the receipt bytes directly.

## Manual acceptance

Record only directly observed clean-install, update, rollback and physical UI
results required by the selected channel. Remote entity state is not visual
evidence.
