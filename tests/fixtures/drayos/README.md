# DrayOS fixtures

Each subdirectory here corresponds to one captured model/firmware combination.

Naming convention: `<model>/<firmware-version>/` (for example
`vigor2927/4.4.5.1/`), matching section 33 of the engineering specification.

Do not commit fixtures containing:

- live credentials (PPPoE/VPN/WiFi passwords, PSKs)
- serial numbers
- public WAN IP addresses
- any other information identifying a specific person's device or network

Redact those values consistently (for example `REDACTED_SERIAL`,
`REDACTED_WAN_IP`) so parser tests can still assert on structure without
depending on real values.

See [CONTRIBUTING.md](../../../CONTRIBUTING.md#contributing-drayos-device-fixtures)
for how to contribute a fixture for a device not yet represented here.

# Provenance

- `vigor2927lac/4.5.2.2/`: sanitised output recovered from the existing
  `vigor2927lac-support` stash, which identifies it as a live-device capture.
  Hostname, WAN addresses, DNS servers, and MAC addresses are redacted.
  Pagination markers are retained. Capture method/date is not recorded.
- `vigor2927/4.4.0/`: documentation examples from the Vigor2927 Series User's
  Guide V2.2, Part X, recovered from the earlier branch. These are not live
  captures and provide regression coverage only.

Tests against these files validate parsing, not transport or live execution.
Never commit credentials, serial numbers, public addresses, or identifying
network names in future fixtures.
