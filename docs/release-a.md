# Release A acceptance criteria (v0.1.0)

This freezes the
[engineering specification's Definition of Done](architecture/engineering-specification.md#77-definition-of-done-for-v010)
into concrete, evidence-backed acceptance criteria. Progress is tracked on
the GitHub **Release A (v0.1.0)** milestone. Functionality is classified as
*implemented*, *fixture-tested*, or *hardware-tested*; only recorded evidence
moves an item between classes.

## Named module list

| Module | Scope shipped in v0.1.0 | Evidence class |
| --- | --- | --- |
| `drayos_command` | Arbitrary operator commands; check mode restricted to `show` | Hardware-tested (read paths) |
| `drayos_facts` | Read-only structured facts with opt-in private subsets | Hardware-tested |
| `drayos_hostname` | Read-only gather/parse; configuration explicitly unsupported | Hardware-tested (read); write excluded by evidence |
| `drayos_dns` | Read all LAN DNS pairs; merged writes only on disabled LAN7, Vigor2927Lac 4.5.2.2 | Hardware-tested within guard |
| `drayos_ntp` | Primary server (index 1) on Vigor2927Lac 4.5.2.2 | Hardware-tested within guard |
| `drayos_tr069` | Read-only single-leaf and next-level name queries | Hardware-tested (reads) |

Platform plugins (terminal, cliconf) and the shared `module_utils` transport
are required and hardware-tested on the qualified combination.

## Evidence requirements

- Every claimed runtime and device combination appears in the
  [qualification matrix](qualification-matrix.md) with an executable test.
- Live claims cite AWX job IDs, revisions, model, and firmware in the
  [device matrix](supported_devices.md).
- Write modules satisfy the mandatory resource test matrix: changed and
  unchanged runs, both check-mode predictions, rejection/timeout/connection
  loss, readback mismatch, invalid input, and sensitive-path redaction.
- CI is green on the release revision: baseline, lint/build/installed smoke,
  three unit matrix rows, docker sanity, CodeQL.
- The release artefact is built from a clean tree and inspected
  (`tests/unit/test_collection_build.py`).

## Explicit non-goals for v0.1.0

- **Hostname configuration** — two authorised attempts failed readback and
  the documented `sys name` command is a WAN DHCP-name setting; see
  [hostname evidence](hostname.md). Excluded until a management-name
  interface is independently qualified.
- **TR-069 writes**, secondary NTP, time enablement, writes on enabled LANs,
  and reboot-persistence claims — no qualifying evidence.
- **Live libssh support** — unit-level coverage only.
- **Configuration backup, LAN/route/VLAN/DHCP-pool/SNMP/account/NAT/
  firewall/VPN management** — Release B backlog.
- **VigorSwitch, VigorAP, VigorACS, DrayOS 5** — separate future programmes;
  vendor catalogues alone establish no support.
- Ansible certification or vendor endorsement.

## Remaining release gates

The open gates before tagging v0.1.0 are hardware-bound and tracked as
milestone issues: release-candidate hardware qualification of the built
artefact, candidate acceptance with rollback rehearsal, and the publication
run itself. Each requires operator approval for any device write.
