# Hostname resource

**Configuration is blocked by a failed hardware qualification. Do not use
`merged`, including its check-mode command prediction, for production changes.**
The original management name was independently verified after both failed
attempts. PR #16 remains a draft while the correct write interface is investigated.

`kpeacocke.draytek.drayos_hostname` implements one declarative resource using
the existing `network_cli` connection. It supports:

- `gathered`: return `gathered: {hostname: ...}` using `sys version`.
- `parsed`: return `parsed: {hostname: ...}` from supplied `running_config`
  containing `sys version` output, without a connection.
- `merged`: compare `config.hostname` with the current name, execute
  `sys name <hostname>` only on difference, reread `sys version`, and require
  an exact match.

It does not implement deletion, implicit defaults, reboot, a separate save
operation, or persistence guarantees across reboot. A scalar hostname has no
additional resource fields to preserve or override, so redundant
`replaced`/`overridden` states are not exposed.

## Evidence and support boundary

The [DrayTek UK hostname/SNMP guide](https://www.draytek.co.uk/support/guides/kb-vigor-snmp-name)
documents `sys name my.router`, but that generic guidance does **not** establish
management-hostname configuration on this model. The
[Vigor2927 command manual](https://www.draytek.com/online-manuals/router/v2927/v4.4.6.2/command/)
instead documents `sys name <wan1/wan2> <ASCII string>` as a WAN DHCP-name
setting. AWX jobs 1946 and 1951 attempted the approved temporary management name
and failed mandatory readback; cleanup and independent reads verified the
original name. No successful management-hostname write is established.

The read format comes
from the sanitised Vigor2927Lac 4.5.2.2 `sys version`
[fixture](../tests/fixtures/drayos/vigor2927lac/4.5.2.2/sys_version.txt),
also exercised by read-only AWX qualification.

Read-only inspection on 16 November 2026 of that model/firmware's management
UI found a router-name input with `maxLength=39`. No field was edited or
submitted. This is UI evidence, **not** a measured CLI maximum: the module's
supported input subset is 1-39 ASCII letters, digits, dots, underscores or
hyphens, beginning with a letter or digit. Single-token names avoid command
injection and remain compatible with the collection's prompt recogniser.
Spaces, quoting, control characters, Unicode names and longer names are
deliberately unsupported rather than escaped speculatively.

Configuration, including check-mode planning, is restricted to the exact
Vigor2927Lac/4.5.2.2 model/firmware pair. Other targets fail before any
configuration command. Gathered/parsed states use the existing read format;
other models still require separate parser/transport qualification.

**The write workflow is offline-tested and failed hardware qualification.**
The generic command assumption was contradicted by the model-specific manual
and device readback. The UI constraint does not prove SSH write
behaviour, exact CLI limits or persistence on this firmware. Before production use,
replace the incorrect command mapping with a verified interface and complete
authorised write/readback/idempotency and recovery tests on an approved
target. Keep the previous name and an independent management route available.

The engineering specification originally proposed TR-069-backed resources.
The model-specific manual documents `sys tr069 get <parm> nextlevel` for
names-only discovery. The separate
[read-only inspection playbook](../tests/awx/inspect_vigor2927lac_cli.yml)
uses that grammar for the documented DeviceInfo and vendor System subtrees.
Parameter mappings and a writable management-hostname leaf remain unverified.
No speculative TR-069 service or generic resource engine is introduced.

## Example

Use the [normal inventory and verified SSH configuration](../README.md#read-only-quick-start).
Begin with a read and a check-mode prediction:

```yaml
- name: Gather the current hostname
  kpeacocke.draytek.drayos_hostname:
    state: gathered

- name: Predict a change without writing
  kpeacocke.draytek.drayos_hostname:
    config:
      hostname: branch-router
  check_mode: true
  diff: true
```

Do not remove `check_mode: true` while the write-interface blocker remains.
After a corrected interface is qualified and explicit change/recovery approval
is obtained, a second identical execution must report `changed: false`
and send no configuration command. Hostnames are compared case-sensitively;
the module does not silently trim or case-fold desired values.

In check mode, `after` and `commands` describe the prediction, not a verified
change. In normal mode, `after` is returned only after successful readback.
Diffs contain only hostname dictionaries, never complete version output.
The `running_config` argument is marked `no_log` because version output can
contain device identifiers.

Rejected commands, timeouts, lost connections, malformed reads and mismatched
readback fail explicitly. Transport exception text is suppressed to avoid
exposing device output. An attempted write followed by any failure reports
`changed: true` conservatively: the device may have changed, but the result
is unverified. It does not retry, roll back automatically, or report a
success-shaped `after` value. Inspect the router through the approved
management route before retrying.

## Offline verification

```sh
python -m pytest -q tests/unit/plugins/modules/test_drayos_hostname.py
```

Tests exercise the actual Ansible module entry point with a stateful fake
transport: changed/unchanged, both check-mode cases, second-run idempotency,
diffs, parser errors, platform rejection, input injection, transport failures
at each phase, and acknowledgement followed by mismatched readback.
These tests never connect to a real router.

CI also installs the built tarball into an isolated collection path and runs
`tests/integration/hostname.yml` from outside the source checkout. This
executes the real module payload locally, checks the parsed return shape,
and proves that malformed input fails. It qualifies installation and the
offline parser, not an SSH write.

Keep `ansible_network_single_user_mode: false` (the default). The optional
netcommon command cache is invalidated on configuration-mode transitions or
exact registered configuration commands. DrayOS uses neither mechanism for
`sys name <hostname>`, so cached reads cannot qualify fresh readback.
The cliconf command path now rejects this unsupported mode before sending
commands, rather than allowing resource verification against cached data.
