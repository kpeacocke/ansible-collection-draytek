# Security architecture

This describes the collection's security-relevant design as implemented and
verified. Operational policy (reporting, credential and host-key handling for
users) is in the [security policy](../SECURITY.md).

## Assets

- Device administrator SSH credentials, held in the controller or AWX
  credential store — never in inventory, vars files, or fixtures.
- SSH host keys identifying authorised devices.
- Device state exposed through reads: hostnames, serial numbers, addresses,
  DHCP leases, NAT rules, TR-069 parameter values (which can include
  credentials).
- The published collection artefact and the CI that produces it.

## Trust boundaries and assumptions

- The playbook author and controller are trusted. `drayos_command` passes
  operator-supplied commands by design and does not prevent configuration
  changes in normal mode.
- Device output is untrusted input: every parser validates shape and fails
  closed on unknown, ambiguous, or truncated responses rather than guessing
  (`plugins/module_utils/network/drayos/`).
- The SSH transport is protected by host-key verification; disabling host-key
  checking is out of contract.
- Pull-request-triggered CI is untrusted: workflows grant `contents: read`
  only, and secrets are confined to scheduled/dispatch baseline jobs.

## Input validation before command generation

Every user-controlled value that reaches a device command line is validated
first:

- NTP server names must match a strict hostname grammar before interpolation
  (`plugins/module_utils/network/drayos/ntp.py`).
- DNS addresses are parsed as `IPv4Address` objects; the subcommand is a
  literal (`plugins/modules/drayos_dns.py`).
- TR-069 parameter paths must match a strict path grammar
  (`plugins/module_utils/network/drayos/tr069.py`).
- Facts and hostname reads send hard-coded commands only.

No module path reaches a local shell; commands travel as single CLI lines
over the persistent `network_cli` session.

## Secret and sensitive-output handling

- `running_config` arguments are `no_log` in all modules that accept them.
- `drayos_tr069` refuses to run without task-level `no_log: true`, because
  TR-069 leaves can contain credentials.
- The cliconf plugin rejects private reads (TR-069, DHCP leases, NAT, LTE)
  while persistent command logging is enabled
  (`plugins/cliconf/drayos.py`).
- Transport and command failures suppress raw device output; parser errors
  are static strings that never embed device data.
- Fixtures must be sanitised before contribution
  ([rules](../CONTRIBUTING.md#contributing-drayos-device-fixtures)).

## Privileged operations

- `cliconf.get_config` and `edit_config` are not implemented; there is no
  generic configuration-write path.
- Each write module re-verifies the exact qualified platform before writing
  (`drayos_ntp` primary server on Vigor2927Lac 4.5.2.2; `drayos_dns` only on
  the disabled LAN7 of that firmware), performs mandatory readback, and fails
  with `state_may_have_changed` rather than reporting unverified success.
- Check mode performs reads only; write commands are gated behind
  `changed and not check_mode`.

## Supply chain

- All GitHub Actions are pinned to full commit SHAs and validated by
  `scripts/baseline.py validate` and CI.
- `galaxy.yml` `build_ignore` keeps repository tooling, caches, and local
  artefacts out of the published collection; a unit test inspects the built
  archive (`tests/unit/test_collection_build.py`).
- Dependencies are the official `ansible.netcommon` collection and
  version-bounded development tools (`requirements-dev.txt`).

## Review history

An evidence-based review of input-to-command paths, secret exposure,
privilege boundaries, workflow credentials, and packaging found no
exploitable vulnerability at the reviewed revision; the identified hardening
items (artefact `build_ignore` gaps, a prefix-based check-mode guard, and a
missing `no_log`) were fixed with regression tests in the same change that
introduced this document.
