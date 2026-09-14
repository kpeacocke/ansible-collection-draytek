# Supported devices

This collection's DrayOS support is built from real captured device output
(the [engineering specification's discovery rule](architecture/engineering-specification.md#65-discovery-before-implementation)). DrayTek publishes a Command
Reference per product on its regional Downloads pages, and the CLI is
self-documenting (`?` lists commands), but this collection's normalised
representation must still be validated against real command output before a
parser is written, and coverage grows through fixtures contributed by device
owners; see
[CONTRIBUTING.md](../CONTRIBUTING.md#contributing-drayos-device-fixtures).

These terms are not interchangeable:

- **Supported** — the collection is designed to work with this platform family.
- **Tested** — a sanitised real-device fixture exists for this exact
  product/firmware combination, with hardware verification recorded
  separately where available.
- **Expected compatible** — believed to work by architectural similarity to a
  tested product, but not itself verified.
- **Evidence only** — vendor documentation has been catalogued, but no
  collection transport or runtime support has been established.

Never infer that an entire Vigor family works because one model passed tests.

| Product | Platform | Firmware | Tested | CI Tested | Support Level | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Vigor2927Vac | DrayOS | 4.4.0 | No (documentation-derived) | Yes (catalogue/YAML integrity tests) | Expected compatible | Vendor command evidence is retained; parser implementation is deferred until a real-device fixture exists. See [issue #6](https://github.com/kpeacocke/ansible-collection-draytek/issues/6). |
| VigorAP 1060C | Web UI management evidence | V1.4.9 | No | No | Evidence only | Catalogue records Web UI evidence; no CLI, HTTP or API transport is documented. |
| VigorAP 918R | Web UI management evidence | V1.4.6 | No | No | Evidence only | Catalogue records management evidence; no CLI, HTTP or API transport is documented. |
| VigorSwitch P2100/G2100 | Telnet/console CLI evidence | V2.8.3 | No | No | Evidence only | CLI catalogue exists; SSH parity, readback, idempotency and runtime support are unverified. |
| VigorSwitch G1080 | Web UI management evidence | V1.04.04 | No | No | Evidence only | Catalogue records Web UI evidence; no CLI, HTTP or API transport is documented. |
