# Development

## Environment

- Python 3.11–3.14 with `ansible-core` 2.19 or later.
- Docker, for `ansible-test sanity --docker` only.
- No DrayTek device is needed for unit tests, lint, builds, or the offline
  integration playbooks; live validation is a separate, authorised activity
  (see [testing](testing.md)).

Set up from the repository root:

```sh
python -m pip install -r requirements-dev.txt
ansible-galaxy collection install -r requirements.yml
```

## Everyday commands

```sh
python -m pytest tests/unit          # unit suite
ansible-lint                         # production profile
ansible-galaxy collection build --force
python scripts/baseline.py validate  # repository baseline conformance
python scripts/project_factory.py self-test
```

The full validation sequence, including sanity and the installed-artefact
smoke checks CI runs, is documented in [testing](testing.md).

## Repository layout

- `plugins/terminal/`, `plugins/cliconf/` — DrayOS `network_cli` platform
  plugins (prompt handling, pagination, privacy guards).
- `plugins/module_utils/network/drayos/` — shared connection, parsing,
  platform, and per-resource helpers. Prefer extending these over copying
  logic between modules.
- `plugins/modules/` — the public modules.
- `tests/unit/` — pytest suite, including real netcommon receive-loop tests.
- `tests/integration/` — offline playbooks run against the built artefact.
- `tests/fixtures/drayos/<model>/<firmware>/` — sanitised captured device
  output; see the [fixture rules](../CONTRIBUTING.md#contributing-drayos-device-fixtures).
- `tests/awx/` — AWX fixture and read-only live validation playbooks.
- `scripts/`, `.baseline/` — repository governance tooling, excluded from the
  built collection by `galaxy.yml` `build_ignore`.

## Engineering rules that bite

- Discovery before implementation: never infer DrayOS CLI syntax from
  manuals alone; a parser needs sanitised real output first
  ([specification](architecture/engineering-specification.md#65-discovery-before-implementation)).
- Evidence scope is per model/firmware/transport combination. Do not widen a
  guard, platform check, or documentation claim beyond what a recorded test
  proved.
- Write modules must read back and verify after a write, be idempotent, and
  fail closed when the result is uncertain.
- Carry a changelog fragment under `changelogs/fragments/` with behavioural
  changes.

## Debugging notes

- Reproduce transport behaviour with the unit tests in
  `tests/unit/plugins/terminal/` and the connection tests, which drive the
  actual Paramiko and libssh receive loops with gated fixture pages.
- Run a single module offline through its `tests/integration/targets/`
  playbook using the symlinked layout:
  `ANSIBLE_COLLECTIONS_PATH="$PWD/tests/awx/collections:$HOME/.ansible/collections" ansible-playbook tests/integration/facts.yml -i localhost,`
- Never enable persistent command logging against a real device; private
  reads are rejected while it is active (see [security](security.md)).
- Live failures are investigated through AWX job output and recorded in
  [supported devices](supported_devices.md); see
  [troubleshooting](troubleshooting.md) for operator-facing symptoms.
