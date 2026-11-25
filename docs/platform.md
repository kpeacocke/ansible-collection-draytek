# DrayOS platform guide

This collection implements an `ansible.netcommon.network_cli` platform for
DrayTek routers running DrayOS. It consists of a terminal plugin, a cliconf
plugin, and shared connection utilities; modules communicate only through
this platform.

## Connection configuration

```yaml
ansible_connection: ansible.netcommon.network_cli
ansible_network_os: kpeacocke.draytek.drayos
ansible_user: automation
```

Supply the SSH password or key through a credential store (for example an
AWX machine credential), and verify the device host key out of band. The
validated live transport is Paramiko (`ansible_network_cli_ssh_type:
paramiko`); live libssh operation has not been qualified.

## Terminal behaviour

- The DrayOS prompt ends in `>` followed by trailing whitespace; matching
  accepts trailing horizontal whitespace.
- Paginated output (`--- MORE ---`) is answered with Space, without a
  carriage return, up to 64 pages per command; the persistent command
  timeout bounds stalled output.
- There is no privilege escalation concept: `become` is unsupported and the
  CLI session is already administrative. Restrict the device account
  accordingly.

## Cliconf behaviour

- `get_config` and `edit_config` are deliberately not implemented; there is
  no generic configuration push path. Configuration happens only through
  specific, qualified modules.
- Private reads (TR-069 parameters, DHCP leases, NAT tables, LTE status) are
  refused while persistent command logging is enabled, so raw sensitive
  output cannot land in connection logs.
- `ansible_network_single_user_mode` must stay `false` (the default); DrayOS
  command caching is unsupported and rejected before any command is sent.

## Platform identification

`drayos_facts` identifies the platform from `sys version` output and reports
`discovery_status` (`identified`, `partial`, `ambiguous`, `unrecognised`).
Missing or duplicated model/firmware labels leave the field unset rather
than guessing. Capability metadata is attached only for combinations with
recorded live evidence; see the [device matrix](supported_devices.md).

## Using generic netcommon modules

`ansible.netcommon.cli_command` works through this platform and is subject
to the same privacy guards as the collection's own modules. Prefer
`drayos_command` for its documented check-mode semantics and
`drayos_facts` for structured data.
