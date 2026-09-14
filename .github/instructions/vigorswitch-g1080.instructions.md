---
applyTo: "**/*g1080*,plugins/**,tests/**,docs/architecture/**"
---

# VigorSwitch G1080 evidence rules

Apply these instructions only to G1080 work. Read `docs/command-reference/draytek-vigorswitch-g1080-management.yaml` and its README. Cite record IDs and printed/PDF pages in design rationale.

- Keep G1080 Web UI evidence separate from P2100/G2100 CLI evidence. Do not invent commands, Telnet/SSH support, HTTP endpoints, CGI paths, payloads, SNMP OIDs or APIs.
- Only `manual_evidence` is manual-derived; `proposed_ansible_mapping` is unimplemented design. Unknown values and conflicts must remain explicit. Examples are not defaults.
- Verify model and firmware; evidence is guide v1.0 for V1.04.04, not all switch firmware. Eight physical ports take precedence over stray ten-port prose; do not generate ports 9/10.
- Obtain vendor documentation or authorised lab evidence before choosing a transport. Do not claim idempotency/check mode until real readback, comparison and verification tests establish them.
- Do not silently repair multicast, aggregation, loop or mirroring ambiguities with generic switch knowledge. Troubleshooting STP references do not establish a G1080 STP configuration surface.
- Separate facts from Clear Counters, password/IP changes, restore, reset, firmware upgrade and other actions. Model interruption and recovery explicitly. Do not perform actions while collecting facts.
- Keep secrets out of logs/fixtures/diffs, use no_log where needed, and do not fall back to documented default passwords. Never parse this documentation YAML as runtime configuration logic.
