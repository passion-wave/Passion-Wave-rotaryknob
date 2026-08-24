# Active issues and release acceptance

This is the short current issue index. Resolved findings, earlier Beta evidence,
long logs and superseded acceptance windows are frozen in
[the archive](archive/known-issues-history.md). A release note or remote entity
state is not direct visual evidence.

## Current physical acceptance

| ID | State | Required evidence |
| --- | --- | --- |
| PW-UI-008 | implemented; physical retest open | On Timo and Marco, inspect at least five bright/dark fullscreen covers. No left/right background seam, white line or colored column may be visible. |
| PW-MEDIA-011 | implemented; physical retest open | During rapid title changes, media page and cover screensaver must show the same current title, artist and cover from the selected-player presentation. No previous cover may appear first. |
| PW-QA-001 | open | Complete the full interaction, restart, network-loss, update/recovery and endurance matrix on each physical product. |
| PW-QA-002 | open | Record the same complete evidence independently for the second customer device. |

## Active technical follow-up

### PW-HA-008: Onboarding endpoint choices are hard to distinguish

Physically observed while recommissioning Timo on 2026-08-24 with the Beta-14
integration: the Display/S3 and Bridge selectors do not make the required
choice sufficiently obvious. Replace the current visually similar labels with
an unambiguous product grouping that foregrounds processor role, friendly
device name, MAC suffix and IP/host. Prefer an automatically matched S3/Bridge
pair when exactly one physical product is discoverable, while retaining an
explicit identity confirmation and a clear warning against mixing processors
from different RotaryKnobs. Add config-flow tests for one-product and
multi-product discovery.

### PW-HA-009: Configured identity can be invisible after recommissioning

Observed on Timo on 2026-08-24 after deleting its old PassionWave and ESPHome
entries, reflashing both processors and completing discovery: a repeated
discovery flow aborted with `already_configured`, but no Timo device was
visible below the PassionWave integration. The display nevertheless received a
valid clock. Capture the actual Home Assistant config-entry, device-registry
and entity-registry state before any further deletion. The setup flow should
either expose and load the existing logical product, continue an incomplete
connection flow, or present a recovery action instead of an unactionable
`already_configured` abort.

### PW-WEB-002: Bridge restart required before Wi-Fi setup

Physically observed on Timo during the 2026-08-24 Beta-14 clean install: after
the second-stage Bridge image reached `Installation complete`, the Wi-Fi dialog
did not become available until the Bridge was reset. This is a real onboarding
requirement, not evidence that the flash failed. The installer must show the
RESET or two-second USB power-cycle instruction prominently before the Bridge
install action and provide a separate Improv reconnect action afterwards.
Investigate whether a future Bridge image can enter Improv reliably without the
manual restart; until then the documented restart is the supported workaround.

### PW-MEDIA-009: Playlist track list physical completion

Home Assistant object normalization and real page results are automated/live
verified. The remaining gate is direct display selection and start of tracks
from short and long playlists on both devices.

### PW-MEDIA-010: Latest-command-wins physical completion

The integration serializes Music Assistant commands and discards obsolete
generations. Perform rapid different and repeated selections on hardware and
verify that an older queue build never replaces the latest chosen track.

### PW-LIGHT-004: WLED preset latency

Measured delay is dominated by WLED and stored preset transition time; the
empty-slot retry storm is fixed. Decide the desired transition policy and run
the remaining physical preset retest.

### PW-FW-008: ESPHome deprecations

Migrate `online_image`, `qspi_dbi` and announced build flags before their
removal release. They are warnings, not a current runtime failure.

### PW-HA-006: Weather source ownership

Move final weather-source selection from firmware configuration into the
PassionWave Config Entry.

### PW-HA-007: Historical MQTT registry entries

The runtime is MQTT-free. Remove old registry entities only through an explicit
reviewed migration with user authorization.

## Evidence update rule

For each test record device, wall-clock time, installed integration/S3/Bridge
versions, selected player, expected result and whether evidence was automated,
remotely observed or physically observed. Move completed detail to the archive
when closing an issue; keep this file short and actionable.
