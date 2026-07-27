# ESPHome API security lifecycle

## Decision

An unencrypted ESPHome Native API is acceptable only in the short-lived public
factory-onboarding state. It is not the target configuration for an installed
Rotaryknob.

The supported lifecycle on Home Assistant 2026.7 or newer is:

1. flash a credential-free public factory image;
2. provision Wi-Fi locally with Improv Serial;
3. let Home Assistant discover and adopt both processors;
4. let Home Assistant generate and provision one unique 32-byte API encryption
   key for each processor over the zero-PSK Noise provisioning connection;
5. let each processor persist its key and close its provisioning window;
6. use encrypted Native API for all later Home Assistant connections;
7. install an authenticated managed update profile before treating the device
   as fully commissioned.

Factory and managed firmware share the same versioned S3 and ESP32 cores. They
are deployment profiles, not separate product revisions.

## Why the factory image starts without a key

A public binary cannot contain a private, per-installation key. A shared key in
all shipped images would be public and would not authenticate an individual
device. Conversely, a random key compiled into a public binary would be unknown
to the buyer and reproduce the unwanted Home Assistant encryption-key prompt.

ESPHome 2026.7 and Home Assistant 2026.7 support an `api.encryption` block
without a compiled key. Home Assistant connects through the encrypted zero-PSK
Noise provisioning path, generates a random per-endpoint key, installs it on
the controller and stores the same key locally. The customer neither sees nor
copies the key.

The provisioning window is limited to 20 minutes. If it expires before
adoption, a physical reset or power cycle reopens it. The public factory image
still has a fixed fallback access-point password and unauthenticated ESPHome
OTA. API provisioning therefore removes the customer-visible encryption-key
step, but does not by itself make the public factory profile a final managed
deployment.

## Managed profile requirements

One physical Rotaryknob contains two chips with independent network endpoints
and therefore needs two distinct API keys:

```text
One Rotaryknob
├── S3/display API key
└── ESP32/bridge API key
```

Additional Rotaryknobs repeat this two-endpoint model. Every installation still
uses only two firmware roles: one common S3 core and one common ESP32 core.
Small private device overlays provide the hostname, friendly name, Wi-Fi
credentials, API key, OTA password and installation-specific Home Assistant
targets.

Keys must never be committed, copied into release binaries, printed in
diagnostics or shared between customers. The public `secrets.example.yaml`
contains placeholders only.

The current two-device test installation intentionally uses the already known
private installation key as a migration bridge across its four endpoints. This
is safer than inventing new keys immediately before OTA and risking an
unknown-key lockout, and it removes the plaintext production state in one
controlled step. It is not the final per-endpoint key policy; splitting the
key after every Native API connection is verified remains tracked as
`PW-SEC-001`.

## Migration without losing access

API encryption and the Home Assistant config entry must change together:

1. generate and securely record the two keys for one physical device;
2. build both managed profiles and validate them before touching either MCU;
3. update the S3 first while its current OTA path is still reachable;
4. enter the S3 key when Home Assistant requests it and verify the Native API;
5. update the ESP32 bridge;
6. enter the bridge key and verify both API connections plus the UART link;
7. for a multi-device installation, repeat the process for each additional
   physical Rotaryknob.

Do not enable encryption on both processors simultaneously unless both keys are
already available. A wrong or lost key does not brick the board, but recovery
then requires USB or another still-authorized update path.

## Responsiveness

API encryption stays enabled in the managed performance profile. The local UI
and rotary handling do not wait for Home Assistant round trips. Existing
latency measurements already include encrypted Native API traffic; removing
encryption is therefore not an accepted latency optimization.

## Current project state

- Public `factory-s3.yaml` and `factory-esp32.yaml`: keyless at build time, with
  a 20-minute ESPHome provisioning window and automatic per-endpoint API key
  creation by Home Assistant 2026.7+.
- Every private Managed entrypoint: encrypted Native API and
  password-protected OTA through one shared Managed deployment layer. The
  current two-device test installation has four such entrypoints.
- Installed production pair: migrated to encrypted Managed profiles on
  2026-07-27.
- Installed second pair: encrypted; the consolidated profiles retain its
  stable hostnames and use the same Managed transport policy.
- All endpoints in the current two-device test installation use the known
  private migration key. Splitting it into endpoint-specific keys remains the
  final hardening step.

References:

- [ESPHome security best practices](https://esphome.io/guides/security_best_practices/)
- [ESPHome Native API encryption](https://esphome.io/components/api/)
