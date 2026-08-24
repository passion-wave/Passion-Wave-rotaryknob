# Firmware and integration 3.0.1-beta.14

Release summary: Isolierter Preview-Installer mit erreichbaren Kandidatenartefakten

## Repository scope

- Role: S3, Bridge and Home Assistant implementation.
- Runtime/channel metadata: `VERSION` and the Control release contract.
- OIDs, toolchain digests, gate durations and payload hashes: generated release receipt.

## Automated evidence

Firmware behavior is unchanged from the accepted Beta-13 sources; Beta 14
rebuilds all four Factory/OTA payloads under the new coordinated version so the
isolated Web preview and later HACS/OTA promotion reference one exact SemVer.
The Hosted-CI receipt remains the byte and provenance authority.

## Manual acceptance

Record only directly observed clean-install, update, rollback and physical UI
results required by the selected channel. Remote entity state is not visual
evidence.
