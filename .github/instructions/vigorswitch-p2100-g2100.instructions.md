---
applyTo: "plugins/**/*.py,tests/**/*.py,docs/**/*.md"
---
# DrayTek VigorSwitch P2100/G2100 engineering instructions

Apply these instructions only to vigorswitch-p2100-g2100 work. Do not transfer this device evidence to other models.

Use `docs/command-reference/draytek-vigorswitch-p2100-g2100-telnet.yaml` as the source catalogue for VigorSwitch CLI behaviour.

## Non-negotiable rules

- Do not invent DrayTek CLI syntax, output, defaults, modes, ranges, or feature support.
- Do not assume Cisco IOS semantics because the switch CLI uses familiar words such as `configure`, `interface`, `show`, or `no`.
- Do not assume Telnet and SSH command parity without a captured device test on supported firmware.
- Do not derive `changed` from command execution. Derive it from a comparison of normalised current and desired state.
- Implement read/parser behaviour before mutation for declarative resources.
- Support Ansible check mode wherever current state can be determined without mutation.
- Fail explicitly on unrecognised parser output. Never silently interpret unknown output as a default state.
- Never expose passwords, RADIUS/TACACS secrets, SNMP authentication/privacy secrets, private keys, tokens, or other credentials in module output, logs, exceptions, diffs, or test snapshots.
- Treat reboot, restore-defaults, firmware/configuration copy/upgrade, port shutdown, certificate replacement, and similar operations as disruptive/destructive and require explicit design review before exposing them as normal resource modules.

## Architecture boundary

Keep these concerns separate:

```text
Ansible resource/module
        |
        v
normalised resource model
        |
        +--> state comparator / diff planner
        |
        +--> command builder
        |
        +--> output parser
        |
        v
connection/transport abstraction
        |
        +--> SSH/CLI (preferred when proven)
        +--> Telnet only when explicitly enabled/supported by collection policy
```

Parsers must not generate commands. Command builders must not parse output. Transport code must not encode feature semantics.

## Implementation sequence

For each resource:

1. Prove the read command and capture real output.
2. Add parser fixtures for normal, empty, boundary and malformed output.
3. Define the normalised Python state model.
4. Implement comparison/diff logic.
5. Implement command generation from the diff.
6. Add check-mode tests.
7. Add idempotency tests proving a second run produces `changed: false`.
8. Add integration tests against each firmware version claimed as supported.

## Source-catalogue semantics

`source_reference`, `purpose`, `syntax_items`, `related_syntax`, and `examples` describe or preserve vendor documentation.

`ansible_mapping` is proposed project design only. It is not vendor documentation.

When the catalogue is incomplete or ambiguous: stop implementation, create a traceable TODO, and obtain real-device evidence. Do not guess.
