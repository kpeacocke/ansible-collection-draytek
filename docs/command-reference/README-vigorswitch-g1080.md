# VigorSwitch G1080 management evidence

Source: [User’s Guide v1.0](sources/DrayTek_UG_VigorSwitch%20G1080_V1.0.pdf), firmware V1.04.04, 5 June 2018. The 41-page PDF has four preliminary pages; printed page + 4 gives the physical PDF page. Identity is PDF p2; SHA-256 is in the YAML.

The [catalogue](draytek-vigorswitch-g1080-management.yaml) covers all twelve Chapter 3 management sections in 17 records, with additional access and hardware constraints. Each record separates `manual_evidence` from `proposed_ansible_mapping`. Settings include named controls, known options, explicit defaults/ranges, constraints, behaviours, prerequisites and printed/PDF page references. Null means not established, not unlimited or disabled. Each statement inherits its record page references. Paths are display labels; inner components may be page sections rather than sidebar menus.

This is Web UI evidence, not executable automation or a CLI reference. Do not use P2100/G2100 commands on G1080. The guide supplies no CLI syntax, HTTP endpoint, CGI path, API contract or SNMP management contract. Proposed resource names are design candidates only; transport, readback, idempotency and check mode have not been established.

## Source conflicts requiring device verification

- Eight physical ports are documented, but QoS and mirroring prose mention ten. Do not create ports 9/10.
- Overview describes static trunking while the management section describes LACP. Do not invent a merged aggregation mode list.
- Multicast prose is inconsistent. The screenshot qualifies all-multicast dropping by both unknown-multicast blocking and disabled IGMP snooping. The complete forwarding matrix remains unresolved.
- Loop Detection Only is described as shutting down and later recovering a port. Do not reinterpret this label as passive observation. Troubleshooting STP/RSTP menus are not established by the management chapter.
- The sample management address is truncated in prose. DHCP is explicitly enabled by default; a screenshot address is not a universal default.
- Normal loop status can mean either no loop or disabled detection. Mirroring port direction terminology also needs verification.

The guide is the evidence for historical documented behaviour, not proof on a current device. Capture authorised lab read/write evidence before implementing a resource; use real sanitised parser fixtures and prove read/compare/write/verify, a no-change second run and non-mutating check mode. Keep credentials out of logs; separate statistics from Clear Counters and other side-effecting actions.

The ZIP contains YAML, README, Copilot instructions and validation. The original PDF is kept separately under `sources/`. Validation covers package structure and source references; no device test was run.
