# Read-only hostname

`kpeacocke.draytek.drayos_hostname` reads a router name; it does not support
hostname configuration or predict configuration changes. `gathered` reads
`sys version` over `network_cli`; `parsed` extracts the name from supplied
output without connecting. Both report `changed: false` in normal and check
mode. Unrecognised or ambiguous output fails instead of guessing.

The read format is validated against the sanitised Vigor2927Lac 4.5.2.2
[fixture](../tests/fixtures/drayos/vigor2927lac/4.5.2.2/sys_version.txt)
and read-only AWX qualification. Other models and firmware require separate
validation.

```yaml
- name: Gather the current hostname
  kpeacocke.draytek.drayos_hostname:
    state: gathered
```

Use the [normal inventory and verified SSH configuration](../README.md#read-only-quick-start).
Keep `ansible_network_single_user_mode: false` (the default): DrayOS command
caching is unsupported and rejected before sending commands. Supplied
`running_config` is marked `no_log` because version output can contain device
identifiers. Transport failure messages suppress device output.

## Why configuration is not offered

The [Vigor2927 command manual](https://www.draytek.com/online-manuals/router/v2927/v4.4.6.2/command/)
describes `sys name <wan1/wan2> <ASCII string>` as a WAN DHCP-name setting,
not a verified management-hostname setter. Two authorised attempts with the
previous experimental mapping failed readback; the original management name
was verified over SSH and HTTPS afterwards. Their effect on WAN DHCP names
cannot be excluded because no pre-attempt baseline was captured.

The model-specific interface for changing the management hostname remains
unverified. Do not infer it from similarly named settings or from the
[generic hostname/SNMP guide](https://www.draytek.co.uk/support/guides/kb-vigor-snmp-name).
Configuration can only be introduced after its interface, readback,
idempotency and recovery are independently qualified on an authorised device.

## Verification

`python -m pytest -q tests/unit/plugins/modules/test_drayos_hostname.py`
exercises read/parse, malformed output, transport failure redaction and
rejection of configuration attempts before device access. CI also installs
the built tarball and runs the offline parser integration playbook.
