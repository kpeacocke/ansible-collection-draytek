---
applyTo: "**/*vigorap*,**/*1060c*,plugins/**,tests/**,docs/architecture/**"
---

# VigorAP 1060C Copilot instructions

Apply these instructions only to vigorap-1060c work. Do not transfer this device evidence to other models.

Use `docs/command-reference/draytek-vigorap-1060c-management.yaml` as the evidence base for VigorAP 1060C behaviour.

## Non-negotiable rules

1. **Do not invent CLI commands.**
   The source manual confirms that a Telnet server can be enabled but does not document the Telnet command set.

2. **Do not assume VigorSwitch, VigorRouter, Cisco IOS, Aruba, UniFi or generic Linux syntax applies.**
   Similar concepts do not establish command compatibility.

3. **Do not invent HTTP or CGI endpoints.**
   The manual documents Web UI screens, not a public configuration API.

4. **Separate evidence from design.**
   A YAML field under `ansible_mapping` is a proposed collection design, not a claim about a native DrayTek API.

5. **Preserve documented limits and defaults.**
   Examples include SSID VLAN IDs, client limits, mesh limits, schedule limits, RADIUS defaults and SNMP credential lengths.

6. **Treat secrets as secrets.**
   Passwords, PSKs, RADIUS shared secrets and certificate material must be marked `no_log` in Ansible code and must not be emitted in debug output.

7. **Model disruptive changes explicitly.**
   Reboots, factory reset, firmware upgrade and policy changes that trigger reboot must never be hidden side effects.

8. **Prefer facts before configuration.**
   If the transport has not been validated, implement read-only discovery/facts before writing configuration modules.

9. **State uncertainty.**
   If the manual does not document how a Web UI setting maps to a protocol operation, say `transport mapping unknown` rather than filling the gap.

## Intended architecture

A future collection should keep these layers separate:

- resource model
- facts/parsing
- transport
- device-specific implementation
- tests/fixtures

Do not hard-code Web UI page labels directly into public Ansible module interfaces unless there is a strong reason.
