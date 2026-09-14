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

## Provenance

Fixtures are either:

- captured from a real device (preferred; note the device/firmware in the
  fixture's directory name), or
- taken verbatim from a vendor-published example in an official DrayTek
  Command Reference/User Guide (acceptable as a starting point per
  [the engineering specification's discovery rule](../../../docs/architecture/engineering-specification.md#65-discovery-before-implementation), but must be labelled as such).

`vigor2927/4.4.0/` is the second kind: the example output is copied verbatim
from the Vigor2927 Series User's Guide V2.2, Part X (Telnet Commands), not
captured from a live device. It has not been confirmed to match current
firmware output byte-for-byte. Treat it as documentation evidence only; do
not implement a parser from it until a real-device fixture is available.
