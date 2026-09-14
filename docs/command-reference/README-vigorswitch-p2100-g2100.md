# DrayTek VigorSwitch P2100/G2100 CLI command catalogue

This directory contains a machine-readable catalogue extracted from **Part XIII — Telnet Commands** of the *VigorSwitch P2100/G2100 User's Guide*, Version 1.3, firmware V2.8.3.

The source manual documents the CLI command roots `clear`, `clock`, `configure`, `copy`, `delete`, `disable`, `end`, `exit`, `hardware-monitor`, `ping`, `reboot`, `renew`, `restore-defaults`, `save`, `show`, `ssl`, `terminal`, `traceroute`, and `udld`. The catalogue contains **83 command-family/section records** and retains source text for each record.

## Repository placement

```text
<collection-root>/
├── .github/
│   └── instructions/
│       └── vigorswitch-p2100-g2100.instructions.md
└── docs/
    └── command-reference/
        ├── README-vigorswitch-p2100-g2100.md
        └── draytek-vigorswitch-p2100-g2100-telnet.yaml
```

Keep this catalogue under `docs/command-reference/`. It is **evidence**, not runtime code. Do not import or parse it from Ansible modules at runtime.

## How Copilot should use it

For a proposed module or resource:

1. Locate the relevant command family in the YAML.
2. Read `source_reference`, `syntax_items`, and `related_syntax` before writing command-generation code.
3. Identify a documented read path (`show`, status output, or equivalent) and build its parser first.
4. Normalise current state into a Python data model.
5. Compare current state to desired state.
6. Generate the minimum command set required to converge state.
7. Implement `check_mode` from the calculated diff, not from whether a command would execute.
8. Verify with captured CLI fixtures from the target firmware.

## Evidence versus design

Fields under `source`, `purpose`, `syntax_items`, `related_syntax`, `examples`, and `source_reference` are source-oriented extraction. Fields under `ansible_mapping` are explicitly proposed engineering guidance and must not be represented as DrayTek documentation.

## Review rule

If the manual does not document a behaviour, do not fill the gap with Cisco/Arista/Juniper conventions or model intuition. Record the gap, capture behaviour from a test device, and add a fixture plus a traceable note before implementation.

## Repository installation note

The catalogue YAML is unchanged from the supplied package. Copilot instructions have an explicit model scope; 1060C frontmatter has been normalised. The accompanying ZIP matches these installed files. See the validation report for the original archive hash and the limits of this installation review.
