# Supported devices

This collection's DrayOS support is built from real captured device output
(the [engineering specification's discovery rule](architecture/engineering-specification.md#65-discovery-before-implementation)). DrayTek publishes a Command
Reference per product on its regional Downloads pages, and the CLI is
self-documenting (`?` lists commands), but this collection's normalised
representation must still be validated against real command output before a
parser is written, and coverage grows through fixtures contributed by device
owners; see
[CONTRIBUTING.md](../CONTRIBUTING.md#contributing-drayos-device-fixtures).

These terms are not interchangeable:

- **Supported** — the collection is designed to work with this platform family.
- **Tested** — a sanitised real-device fixture exists for this exact
  product/firmware combination, with hardware verification recorded
  separately where available.
- **Expected compatible** — believed to work by architectural similarity to a
  tested product, but not itself verified.
- **Evidence only** — vendor documentation has been catalogued, but no
  collection transport or runtime support has been established.

Never infer that an entire Vigor family works because one model passed tests.

## Validated DrayOS facts

`drayos_facts` collects read-only `sys version`, `sys iface`, and `show status`
output through the existing `network_cli` connection. It always reports
`changed: false`, including in check mode.

| Model | Firmware | Evidence | Validation scope |
| --- | --- | --- | --- |
| Vigor2927Lac | 4.5.2.2 | Recovered sanitised device-output fixtures | Parser/module/transport regressions and verified-key read-only AWX validation (job #1936); hostname writes failed qualification |
| Vigor2927Vac | 4.4.0 | Vendor documentation examples | Parser regression coverage only; not live-device validation |

The recovered stash labels the Lac fixtures as live-device captures; this PR
preserves that provenance but does not independently establish how they were
captured. Fixture parsing does not prove SSH transport, prompt handling, or
pagination works against the router. The transport now answers the captured `--- MORE ---` prompt with Space,
without a carriage return, for `sys iface` and `show status`. Repeated prompts
are handled up to 64 advances per command; the persistent command timeout
bounds stalled or over-limit output. Tests exercise the actual netcommon
Paramiko and libssh receive loops with gated multi-page responses.
Live AWX job [#970](https://awx.ambitiouscake.com/jobs/playbook/970/output)
validated revision `04313ae`: all facts completed, hostname was populated,
interface 11 and WAN 6 were present, and the router reported `changed=false`.
The live command prompt ends with two spaces after `>`; terminal matching
accepts trailing horizontal whitespace, with receive-loop regression coverage.
Do not infer support for other models or firmware from these fixtures.

AWX job [#1936](https://awx.ambitiouscake.com/jobs/playbook/1936/output)
requalified read-only facts at `1a583f0` with the device-only limit,
independently verified host key and fail-closed SSH policies. Merged main
`f84d182` has the same Git tree. Facts reported no device changes.

On the experimental hostname branch, jobs 1946 and 1951 failed mandatory
temporary-name readback. The original name was verified over SSH and HTTPS.
This is **not** hostname-write support; the
[hostname evidence](hostname.md) explains why configuration is not offered.
Read-only explicit-Paramiko help job 1953 and names-only TR-069 discovery
job 1956 succeeded. Discovery proves only those reads, not a writable
parameter mapping or a live libssh connection.

## Numbered LAN profiles

Set `gather_lan_profiles: true` on `drayos_facts` to read the configured IPv4
address, netmask and DHCP fields for LAN1 to LAN8. The option is independent
of `gather_subset` and defaults to off. This does not read active leases,
include the separate routed profile, or change configuration. AWX discovery
job [2124](https://awx.ambitiouscake.com/jobs/playbook/2124/output) confirmed
the eight-profile response framing on Vigor2927Lac firmware 4.5.2.2.

## IPv4 route status

Set `gather_ipv4_routes: true` on `drayos_facts` to read the IPv4 table
reported by `ip route status`. Each entry includes a CIDR destination,
the reported flags, the outgoing interface and a next hop (null for
directly connected routes). The option defaults to off and is independent
of `gather_subset`. Use task-level `no_log: true` when route topology
should not appear in job output, and keep persistent transport logging
disabled.

[AWX job 2144](https://awx.ambitiouscake.com/jobs/playbook/2144/output)
verified that normal and check mode returned the same complete table on
the Vigor2927Lac running 4.5.2.2. This does not cover IPv6, policy routing,
or route configuration.

## Configured VLAN slots

Set `gather_vlan_slots: true` on `drayos_facts` to read slots 0 to 15,
including each slot's enable flag, VID, priority, LAN and membership
labels. This opt-in reports configured slots, not the global VLAN enable
flag, effective forwarding state, or untagged management access.
Use task-level `no_log: true` and disable persistent transport logging
when VLAN topology should not appear in job output.

On Vigor2927Lac firmware 4.5.2.2, `gather_vlan_p1_untagged_access: true`
reads the configured permission for devices sending untagged traffic on
P1 to access the router. This independent opt-in returns the boolean
`vlan_p1_untagged_access`; it does not test reachability or report global
VLAN enablement. If the device does not report a recognised setting, the
requested read fails rather than returning an assumed value.

## NAT port-redirection status

On Vigor2927Lac firmware 4.5.2.2, `gather_nat_redirects: true` reads the
documented `srv nat status` table. The returned `nat_redirects` entries
preserve every reported row, including all-zero placeholders; they do not
claim that a row is active or represent the full firewall policy. The parser
fails on unknown or incomplete rows. These values include internal IPv4
addresses and ports: disable persistent command logging and use task-level
`no_log: true`; consider whether fact caching is appropriate. This opt-in has
only been validated on Vigor2927Lac firmware 4.5.2.2.

## WAN link and LTE access facts

`gather_wan_links: true` reads the online and stall indicators from numbered
WAN and PVC WAN headers. It does not report addressing, throughput or other
status blocks. `gather_lte_access: true` reports the modem's LTE access
technology, not link reachability or signal quality. It excludes modem and
subscriber identifiers and requires persistent transport logging to be off.
Both options are independent of `gather_subset` and default to off.

## IPv4 DHCP lease status

`drayos_facts` with `gather_dhcp_leases: true` reads the IPv4 DHCP lease
table independently of `gather_subset`. It returns each row's LAN, displayed
index and lease time, IP address, MAC address and optional host ID. This is
a point-in-time read, not a way to manage reservations, clients or pools.
Persistent transport logging must be off. Use task-level `no_log: true` to
keep client identifiers out of job output, and account for any configured fact cache.

## Primary NTP server

The [NTP resource](ntp.md) is restricted to Vigor2927Lac firmware 4.5.2.2.
Authorised AWX job 2055 proved the index-1 primary-server command, readback and
restoration; independent checks 2053 and 2056 matched the original baseline.
At `4ac10e8`, AWX fixture job 2059 passed 190 tests and live job 2060 verified
gathering and both check-mode predictions without device changes. Separately
approved job 2061 passed an actual module change, readback, identical repeat
(`changed: false`), check-mode prediction without mutation, and restoration.
Independent read-only job 2062 at the same revision matched the original baseline.
These live checks used Paramiko. No secondary-server setter, clock
synchronisation, unrelated time-setting preservation or reboot persistence is
claimed. Other models and firmware fail the module's write-platform guard.

## TR-069 reads

The [read-only TR-069 module](tr069.md) passed single-leaf product reads,
next-level DeviceInfo names and check-mode validation on Vigor2927Lac
firmware 4.5.2.2 with Paramiko. This does not qualify TR-069 writes, other
firmware, or other models.

## LAN DNS readback

Live LAN DNS validation [job 2107](https://awx.ambitiouscake.com/jobs/playbook/2107/output)
on Vigor2927Lac firmware 4.5.2.2 (`b4c923a`) used Paramiko and the verified SSH
host key. `drayos_dns` returned matching primary/secondary IPv4 settings for
all eight LANs in normal and check mode without changes.

Separate, operator-approved Ansible playbook runs validated the CLI mapping
for primary DNS on a disabled LAN7. [Job 2110](https://awx.ambitiouscake.com/jobs/playbook/2110/output)
set a temporary address, and [job 2113](https://awx.ambitiouscake.com/jobs/playbook/2113/output)
restored the field to unset using `srv dhcp dns1 lan7 0.0.0.0`. Both compared all
LAN DNS fields before and after the operation. Independent read-only
[job 2115](https://awx.ambitiouscake.com/jobs/playbook/2115/output) confirmed
that both LAN7 DNS settings were unset. These tests do not qualify changes
on active LANs, effective resolver selection or reboot persistence.
The public `drayos_dns` module restricts `state: merged` to
disabled LAN7 on this exact firmware and verifies all eight LAN DNS pairs
after a write. Use `primary_server: "0.0.0.0"` to clear the field.
[Job 2117](https://awx.ambitiouscake.com/jobs/playbook/2117/output) at `2c76a32`
verified both check-mode predictions and unchanged readback.
[Job 2120](https://awx.ambitiouscake.com/jobs/playbook/2120/output) at `f7496dd`
verified the public module's set, unchanged repeat, clear and full baseline
restoration. An independent read-only
[job 2122](https://awx.ambitiouscake.com/jobs/playbook/2122/output) at the same
revision confirmed both LAN7 DNS fields were unset.

For secondary DNS, operator-approved [job 2367](https://awx.ambitiouscake.com/jobs/playbook/2367/output)
used the documented `srv dhcp dns2` command to set and clear disabled LAN7,
comparing all LAN DNS fields. Independent read-only
[job 2369](https://awx.ambitiouscake.com/jobs/playbook/2369/output) confirmed
both LAN7 fields were unset. The public module accepts `secondary_server` for
the same guarded target. [Job 2372](https://awx.ambitiouscake.com/jobs/playbook/2372/output)
at `5df68bc` verified its changed and unchanged check-mode predictions and
unchanged readback. Separately approved
[job 2376](https://awx.ambitiouscake.com/jobs/playbook/2376/output) at
`ffa7e9d` verified the module's set, unchanged repeat, clear and full baseline
restoration. Independent read-only
[job 2378](https://awx.ambitiouscake.com/jobs/playbook/2378/output) confirmed
both LAN7 DNS fields were unset. Supply either `primary_server` or
`secondary_server` per task, not both; use `"0.0.0.0"` to clear the selected
field. Enabled LANs, other firmware and reboot persistence remain unqualified.

## AWX fixture validation

Use `tests/awx/validate_vigor2927lac.yml` in an AWX project pinned to the PR
revision, with a localhost inventory and no device credentials. The execution
environment needs Python with `venv` support and access to the Python package
index. The job creates a temporary collection layout and virtual environment,
runs the targeted tests, and removes its temporary directory even on failure.
Record the AWX job ID and `scm_revision` with the result. This job tests fixtures
and mocked module execution; it does not contact or validate a live router.


`tests/awx/validate_vigor2927lac_live.yml` uses the existing `HomeOne` inventory
host and its AWX SSH credential for a read-only check. It asserts model,
firmware, nonempty hostname, interface 11 and WAN 6, without logging device
facts. A playbook-adjacent collection layout links directly to the project plugins
so validation executes the checked-out revision even on workers whose
configured collection paths do not match their execution directory.
It changes no router configuration.

## Additional evidence-only families

| Product | Platform | Firmware | Tested | CI Tested | Support Level | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| VigorAP 1060C | Web UI management evidence | V1.4.9 | No | No | Evidence only | Catalogue records Web UI evidence; no CLI, HTTP or API transport is documented. |
| VigorAP 918R | Web UI management evidence | V1.4.6 | No | No | Evidence only | Catalogue records management evidence; no CLI, HTTP or API transport is documented. |
| VigorSwitch P2100/G2100 | Telnet/console CLI evidence | V2.8.3 | No | No | Evidence only | CLI catalogue exists; SSH parity, readback, idempotency and runtime support are unverified. |
| VigorSwitch G1080 | Web UI management evidence | V1.04.04 | No | No | Evidence only | Catalogue records Web UI evidence; no CLI, HTTP or API transport is documented. |
