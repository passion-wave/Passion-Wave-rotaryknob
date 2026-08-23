# Firmware and integration 3.0.1-beta.12

Release summary: A+-Baseline-Kandidat für reproduzierbare Releases und eine kontrollierte Passion-Wave-Web-Produkterweiterung

## Repository scope

- Role: S3, Bridge and Home Assistant implementation.
- Runtime/channel metadata: `VERSION` and the Control release contract.
- OIDs, toolchain digests, gate durations and payload hashes: generated release receipt.

## Automated evidence

Beta 12 carries the unified current-media snapshot used by media view and cover
screensaver, the corrected full-frame artwork rendering and the consolidated
integration/device update workflow onto the current protected main branch.
The automated suite must qualify both Home Assistant versions, all managed and
factory profiles, and both ECUs from the exact committed source OID.

Factory S3 and Bridge builds now initialize and reuse the deterministic
ESPHome tool cache serially. This removes a download-retry race in which two
parallel ESP-IDF installers could invalidate each other's tool directory.

Only the fresh Hosted-CI receipt is publication authority. Local build hashes
are diagnostic and must match the hosted `linux/amd64` payloads byte for byte.

## Manual acceptance

Record only directly observed clean-install, update, rollback and physical UI
results required by the selected channel. Remote entity state is not visual
evidence.

Direct hardware acceptance still has to confirm boot timing, full-frame cover
art without edge stripes, and synchronized title/artist/cover transitions.
