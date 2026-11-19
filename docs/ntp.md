# NTP server configuration

`kpeacocke.draytek.drayos_ntp` gathers both NTP server fields and manages the
primary server over `ansible.netcommon.network_cli`. Configuration is restricted
to **Vigor2927Lac firmware 4.5.2.2**. It does not configure the secondary server,
clear servers, change the clock, time zone or synchronisation mode.

## Behaviour

```yaml
- name: Set the primary NTP server
  kpeacocke.draytek.drayos_ntp:
    state: merged
    config:
      primary_server: time.cloudflare.com
  no_log: true
```

The module validates an ASCII DNS name before connecting, reads the platform
and both current servers, and sends `sys time server 1 <server>` only if the
primary differs. Names compare case-insensitively. After a write, both server
fields must match the requested primary and unchanged secondary. A subsequent
identical invocation sends no configuration command.

`--check` reads the platform and current servers and predicts the result without
writing. `--diff` includes normalised before/after fields; these contain server
names, so use `no_log` if they must remain private. DNS validation is not a
promise that the device accepts every syntactically valid name. A rejection or
readback mismatch fails explicitly.

Use `state: gathered` to read both fields, or `state: parsed` with
`running_config` containing `sys time show` output to parse without a connection.
Missing, duplicate or malformed server fields fail instead of becoming defaults.
An explicitly empty field remains an empty string.

## Qualification evidence

On 19 November 2026, AWX job
[2055](https://awx.ambitiouscake.com/jobs/playbook/2055/output), at
`8f37d831bc91dccafbfe9d9d0e34913ef3abe175`, passed the specifically authorised
temporary test: server index 1 changed the primary to `time.cloudflare.com`,
the secondary remained empty, and the original settings were restored.
Independent read-only jobs
[2053](https://awx.ambitiouscake.com/jobs/playbook/2053/output) before and
[2056](https://awx.ambitiouscake.com/jobs/playbook/2056/output) after the test
matched the previously captured original baseline.

This proves the command mapping and the bounded restoration, not yet a live
write through the new resource module, secondary-server configuration, NTP
reachability, successful clock synchronisation or persistence across reboot.
The parser tests use synthetic server values with the label/bracket format
checked by that live qualification; they are not unredacted device captures.

## Failure and recovery

A failure before a write reports `changed: false`. Once a configuration command
has been attempted, failures report `changed: true` and
`state_may_have_changed: true`, including timeouts and lost connections. No
automatic rollback is attempted: a remote write can take effect even if its
response is lost. Inspect current state independently before retrying.
Transport error text is suppressed so raw device output cannot appear in errors.

AWX's intermittent worker-stream failure remains unresolved. A successful
readback does not establish that the infrastructure fault is fixed. Keep an
independently accessible recovery route for production qualification.
The approval-gated test playbook changes a real router and must never be
scheduled or launched without the exact operator approval and recovery standby.
