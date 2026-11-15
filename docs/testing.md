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
