# DrayOS fixtures

Each subdirectory here corresponds to one captured model/firmware combination.

Naming convention: `<model>_<firmware-version>/` (for example `vigor2927_4.4.5.1/`).

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
