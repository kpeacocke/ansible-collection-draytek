# Contributing

## Before coding

- Read `AGENTS.md` and applicable repository instructions.
- Keep changes focused on one outcome.
- For non-trivial design choices, record an ADR under `docs/decisions/`.

## Before opening a pull request

Run:

```bash
python scripts/baseline.py doctor
```

Then run repository/profile-native tests and checks. In VS Code, `/preflight` runs the author-side readiness protocol.

Pull requests must state what changed, why, verification evidence, risk/rollout considerations, and what was intentionally left out of scope.

## Contributing DrayOS device fixtures

DrayTek publishes a Command Reference per product (on its regional Downloads
pages, alongside the User Guide) and the CLI is self-documenting (`?` lists
commands, `<command> ?` shows sub-commands). Even so, this collection's
DrayOS support (parsing, facts, platform detection) must still be built and
verified from real captured device output, not assumed from documentation
alone (engineering-specification.md, sections 65 and 78.3). One person's set
of devices can only prove so much — coverage across the Vigor range depends
on fixtures from other owners too.

If you have access to a DrayTek device not yet listed in
[docs/supported_devices.md](docs/supported_devices.md), you can help by:

1. Capturing the raw output of relevant CLI commands (see existing fixtures
   under `tests/fixtures/drayos/` for the shape once they exist) with any
   secrets/PII (serial numbers, WAN IPs, PPPoE credentials, PSKs) redacted.
2. Opening a pull request adding the fixture plus your device's
   model/firmware to the supported-devices table.
3. Never submitting fixtures containing live credentials or from a device you
   don't have authorisation to capture output from.

A model/firmware combination only moves from "expected compatible" to
"tested" once a real fixture exists for it.

