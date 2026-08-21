# Firmware and integration 3.0.1-beta.10

Release summary: Canonical linux/amd64 builder platform and customer-visible update acceptance flow

Public Factory and OTA binaries are now always built by the digest-pinned
`linux/amd64` ESPHome image, including on Apple Silicon. Build metadata and the
SBOM record this platform so local and hosted receipts qualify identical bytes.

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
