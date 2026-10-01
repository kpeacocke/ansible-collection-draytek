---
applyTo: "**/*vigorap*,**/*918r*,plugins/**,tests/**,docs/architecture/**"
---

# VigorAP 918R evidence contract

Apply these rules when work concerns VigorAP 918R. Other platforms keep their own evidence and rules.

1. Read `docs/command-reference/draytek-vigorap-918r-management.yaml` and its README before designing or changing 918R support. Cite record IDs and printed/PDF pages in implementation rationale.
2. Treat only `manual_evidence` as manual-derived. `proposed_ansible_mapping` contains unimplemented engineering candidates. Never present proposed resource names as existing modules, documented protocols or vendor capabilities.
3. Scope evidence to User's Guide v1.6, firmware V1.4.6, 5 July 2023. Verify model, physical variant, firmware, operation mode and radio band. Never copy router, switch or 1060C syntax or behavior onto 918R.
4. Do not invent CLI commands, HTTP endpoints, CGI paths, APIs, request payloads, app discovery protocols, SNMP OIDs/MIBs or TR-069 parameter paths. Web UI menu labels are not URLs. Telnet enablement proves only CLI existence. Do not implement a guessed transport.
5. Preserve null/unknown values. Do not convert examples to defaults, infer absent ranges, normalize contradictory prose into new behavior, or infer supported combinations from the union of security dropdown choices. Report missing evidence and require vendor or lab verification.
6. Keep management evidence in documentation; do not load this YAML as runtime configuration logic. Proposed Ansible argument names, types and operation classes require separate design and tests.
7. Establish read -> parse -> compare -> plan -> mutate -> verify from actual device evidence. Claim idempotency and check mode only after tests prove them. A second identical run must make no changes. Never treat a successful request as proof of resulting state.
8. Separate read-only observations from actions on the same page. Scans, speed tests, enrollment, Clear, reset, restore, reboot, upgrades and synchronization may have side effects. Never run them implicitly while collecting facts. Central AP Status of Settings reflects router configuration, not local writable load-balance fields.
9. Enforce documented constraints: bandwidth limiting versus Airtime Fairness; band-steering matching SSID/security; WDS 5GHz restriction; one mesh root/seven nodes/three hops; root-only synchronization; schedule dependencies. Do not claim the suggested two-hop deployment is the hard maximum.
10. Plan connection recovery for credential/network changes, MDM Policies reboot and mesh actions. Configuration backup excludes certificates. Root CA is delete/recreate, not editable. Record rollback limits before implementing disruptive operations.
11. Keep secrets out of logs, examples, diffs and fixtures. Use secret storage and Ansible no_log where needed. Do not assume a masked secret is readable or comparable. Neither admin/admin nor the conflicting null-password statement is a fallback credential policy.
12. Keep WLAN ACLs, overload lists, device objects, MDM classifications, app groups and mesh/Central AP roles distinct unless actual evidence proves their relationship. An X on load-balance status is ambiguous. Sensor labels do not prove hardware support.
13. Treat mobile-app workflows as user-surface evidence only. Current app availability and protocol support were not checked. Screenshot-only pages and RD debug views are not stable parser contracts.
14. Document new verified transport/firmware evidence separately, including provenance and sanitized fixtures; do not rewrite manual evidence to make a proposed implementation appear documented. If evidence is insufficient, return an explicit unsupported/unknown result rather than guessing.
