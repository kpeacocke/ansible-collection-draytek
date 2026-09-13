# Supported devices

This collection's DrayOS support is built from real captured device output
(engineering-specification.md, section 65). DrayTek publishes a Command
Reference per product on its regional Downloads pages, and the CLI is
self-documenting (`?` lists commands), but this collection's normalised
representation must still be validated against real command output before a
parser is written, and coverage grows through fixtures contributed by device
owners; see
[CONTRIBUTING.md](../CONTRIBUTING.md#contributing-drayos-device-fixtures).

These terms are not interchangeable:

- **Supported** — the collection is designed to work with this platform family.
- **Tested** — fixtures and/or hardware verification exist for this exact
  product/firmware combination.
- **Expected compatible** — believed to work by architectural similarity to a
  tested product, but not itself verified.

Never infer that an entire Vigor family works because one model passed tests.

| Product | Platform | Firmware | Tested | CI Tested | Support Level | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| _(none yet)_ | DrayOS | | No | No | | Awaiting first captured device fixture (see [issue #6](https://github.com/kpeacocke/ansible-collection-draytek/issues/6)) |
