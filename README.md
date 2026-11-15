# ansible-collection-draytek

This Ansible collection provides SSH-based automation for DrayTek Vigor routers
running DrayOS, using `ansible.netcommon.network_cli`. It currently includes
`drayos_command` and read-only `drayos_facts`; declarative configuration
modules are not yet available.

VigorSwitch, VigorAP and VigorACS are not supported. The
[device matrix](docs/supported_devices.md) distinguishes live validation from
fixture-only evidence; do not assume other models or firmware are compatible.

## Install from a checkout

The collection requires `ansible-core` 2.19 or later and
`ansible.netcommon` 6.0.0 or later. These are declared minimums, not a promise
that every combination has been tested. From this checkout:

```sh
ansible-galaxy collection build
ansible-galaxy collection install kpeacocke-draytek-0.1.0.tar.gz
```

The filename contains the version in `galaxy.yml`. Install the tarball and its
dependencies in the execution environment used by Ansible or AWX.

## Read-only quick start

For a router whose model and firmware have been validated, configure an
inventory with the actual address and an authorised SSH user:

```yaml
all:
  hosts:
    router:
      ansible_host: router.example.invalid
      ansible_user: automation
      ansible_connection: ansible.netcommon.network_cli
      ansible_network_os: kpeacocke.draytek.drayos
```

Supply SSH credentials through an approved secret store or AWX credential, not
the inventory. Configure and verify the host key rather than disabling host-key
checking. Collect facts with:

```yaml
---
- name: Collect DrayOS facts
  hosts: router
  gather_facts: false
  tasks:
    - name: Gather default facts
      kpeacocke.draytek.drayos_facts:
      no_log: true
```

Facts may contain serial numbers, addresses and other sensitive information;
avoid logging them. `drayos_command` accepts arbitrary device commands and
does **not** prevent configuration changes in normal mode. Use only commands
known to be read-only on the target device.

See [testing](docs/testing.md), [contributing](CONTRIBUTING.md), the
[security policy](SECURITY.md), and the
[GPL-3.0-or-later licence](https://spdx.org/licenses/GPL-3.0-or-later.html).

This repository is governed by engineering baseline **0.5.1** using the **ansible** profile.

## Normal workflow

Verify the local baseline and GitHub settings:

```powershell
.\baseline.ps1 doctor
```

The source repository is recorded in `.baseline/state.json`; no separate GitHub repository variable is required.

Request an update from the central golden baseline:

```powershell
.\baseline.ps1 update
```

For local-only structural/drift diagnosis:

```powershell
python .\scripts\baseline.py doctor
```

In VS Code, use `/plan`, `/implement`, `/debug`, `/verify`, `/review`, `/preflight`, and `/ship`. Durable methodology lives in `.github/skills/`; repository-specific guidance can extend the managed instructions without replacing it.

## Scheduled baseline updates

Configure the repository Actions secret `BASELINE_UPDATE_TOKEN` before publishing
automated baseline updates. Use a fine-grained personal access token restricted to
this repository with Contents, Pull requests, and Workflows read/write permissions,
or a classic token with `repo` and `workflow` scopes. Do not put the token in Git.
The updater uses this credential for checkout, Git pushes, and PR creation, so
workflow-file updates are authorised and PR CI can run.

`GITHUB_TOKEN` cannot be granted a `workflows` permission. Without
`BASELINE_UPDATE_TOKEN`, a current baseline can still be checked, but publishing
pending changes fails explicitly. For a private baseline source repository,
configure a separate read-only `BASELINE_READ_TOKEN`.

## Repository-specific documentation

The collection's engineering specification is the source of truth for scope, architecture and
milestones: [docs/architecture/engineering-specification.md](docs/architecture/engineering-specification.md).

Vendor-derived device evidence is indexed in
[docs/command-reference/CATALOGUES.md](docs/command-reference/CATALOGUES.md). These catalogues
inform future implementation; they do not by themselves establish runtime device support.

Add further setup, operation and usage documentation under `docs/` as the project takes shape.
