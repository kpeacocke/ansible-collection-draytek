# Testing

## Local checks

Install the development dependencies and collection dependencies from the
repository root:

```sh
python -m pip install -r requirements-dev.txt
ansible-galaxy collection install -r requirements.yml
```

Run the local unit suite, lint and collection build:

```sh
python -m pytest tests/unit
ansible-lint
ansible-galaxy collection build --force
python scripts/project_factory.py local-doctor
python scripts/project_factory.py self-test
python scripts/baseline.py validate
```

CI also runs `ansible-test sanity --docker default -v -- plugins/ tests/`
from a checkout located under `ansible_collections/kpeacocke/draytek`, with
the collection dependencies installed alongside it. Docker and the
Ansible test containers are required for that command.

## Fixtures and device validation

Tests under `tests/unit/` use sanitised fixtures and mocks; they do not prove
live connectivity or device behaviour. Fixture provenance and hardware
coverage are recorded in the [device matrix](supported_devices.md). Follow
the [fixture contribution instructions](../CONTRIBUTING.md#contributing-drayos-device-fixtures)
before capturing or sharing output.

The AWX playbooks described in the device matrix include a fixture-only check
and a separate read-only live facts check. Run the latter only on an
authorised device, and record its model, firmware, job ID and checked-out
revision. The live check collects sensitive facts with logging suppressed; it
does not validate configuration changes.

The fixture-only AWX playbook runs the full unit suite in a temporary Python
environment. It copies the repository governance scripts, catalogue and workflows
alongside the collection because the unit tests cover those files too. Collection
dependencies are forcibly installed into that temporary layout, even when the
execution environment already has them elsewhere; the isolated Python interpreter
must be able to import them. The temporary layout is removed after the run.

For the live AWX check, supply `drayos_validation_known_host` as an extra variable
containing the router's previously verified public `known_hosts` entry. Its first
field must be the inventory's `ansible_host` (or `[host]:port` for a non-default
SSH port), not a hashed hostname or an entry for another device. Obtain it
from a trusted client or an independently verified source, not an unverified
`ssh-keyscan` result. Never supply a password or private key in this variable.
The playbook installs that entry into the execution environment's SSH trust store
with logging suppressed, and requires host-key checking even when AWX disables it
through its environment. The project's `ansible.cfg` disables automatic trust of
unknown SSH keys for both transport backends. A missing or mismatched key must
fail rather than falling back to an unverified connection. This setup changes only
the job's execution environment, not the router.

Preparation and policy checks are pre-tasks of the device play, with local work
delegated to the execution environment. They still run with a device-only limit,
and any failure stops that host before the facts tasks. Backend-specific
host-key-checking settings are enforced alongside the generic settings; unsafe
extra-variable overrides are rejected rather than silently taking precedence.
