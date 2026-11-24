# Troubleshooting

Symptoms and causes below are limited to behaviour observed on validated
devices (see the [device matrix](supported_devices.md)). Validate against
your model and firmware before assuming equivalence.

## Connection and transport

- **`couldn't resolve module/action 'kpeacocke.draytek...'`** — the
  collection is not on the configured collections path. Install the built
  tarball and check `ANSIBLE_COLLECTIONS_PATH`; do not run playbooks from
  the source tree without a collection layout.
- **Host key failures** — the contract requires a verified host key. Verify
  and pin the device key out of band rather than disabling host-key
  checking.
- **Timeouts mid-command** — paginated output (`--- MORE ---`) is answered
  automatically up to 64 pages; beyond that, or on a stalled channel, the
  persistent command timeout fails the task deliberately. Raise
  `ansible_command_timeout` only if the device genuinely produces more
  output.
- **`single_user_mode` rejection** — DrayOS command caching is unsupported.
  Keep `ansible_network_single_user_mode: false` (the default).
- **Empty or `None`-shaped responses** — the collection rejects empty and
  Python-literal responses from the transport. A dropped connection can be
  indistinguishable from the literal text `None`; if this occurs, treat the
  run as unreliable and check device reachability.

## Module behaviour

- **`only show commands are supported` in check mode** — `drayos_command`
  check mode only permits commands whose first word is exactly `show`,
  because other commands cannot be proven read-only.
- **Private reads fail with a logging error** — TR-069, DHCP lease, NAT and
  LTE reads are refused while persistent command logging is enabled.
  Disable persistent logging on the connection.
- **`drayos_tr069` requires `no_log: true`** — set it at task level; the
  module fails closed otherwise because parameter values can contain
  credentials.
- **Write refused on an unqualified platform** — `drayos_ntp` and
  `drayos_dns` verify the exact model and firmware before writing and fail
  on anything outside their qualified scope. This is intentional; see each
  module's document ([ntp](ntp.md), [hostname](hostname.md),
  [tr069](tr069.md)).
- **`state_may_have_changed` failures** — a write was sent but readback did
  not confirm the result. Inspect the device manually before retrying; the
  module will not report unverified success.
- **Ambiguous platform identification** — facts leave model/firmware unset
  and report `discovery_status` as `ambiguous` or `unrecognised` instead of
  guessing. Capture the raw `sys version` output and compare it with the
  fixtures before filing an issue.

## Reporting

File issues at the
[issue tracker](https://github.com/kpeacocke/ansible-collection-draytek/issues)
with the collection version, ansible-core version, device model and firmware,
and sanitised output. Suspected vulnerabilities go through the
[security policy](../SECURITY.md), not public issues.
