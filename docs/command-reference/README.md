# DrayTek Vigor2927 Command Catalogue

This directory is intended to be placed in an Ansible collection repository as:

```text
docs/command-reference/
  draytek-vigor2927-telnet.yaml
```

The YAML catalogue is derived from **Part X — Telnet Commands** of the supplied DrayTek Vigor2927 Series User's Guide.

## Purpose

The catalogue is an evidence source for GitHub Copilot and human contributors. It is not itself an Ansible API and should not be exposed directly as the collection's public module interface.

Each record contains:

- a unique `id`
- the documented command heading
- source PDF and printed-manual page ranges
- the introductory description
- syntax text where the manual provides a `Syntax` section
- syntax-description / parameter text
- examples
- complete cleaned source text for the command section

The complete source text is deliberately retained so that extraction heuristics do not become the sole source of truth.

## Important limitation

The vendor manual documents a **Telnet command interface**. The catalogue does not assert that the same command behaviour is available over SSH. That must be validated independently before the Ansible collection uses `network_cli` over SSH for a given command family.

Likewise, the catalogue does not label commands as safely idempotent merely because they have read and write-looking syntax. Idempotency must be proven from an actual read/compare/write workflow.

## Recommended repository placement

```text
.github/
  copilot-instructions.md

docs/
  command-reference/
    README.md
    draytek-vigor2927-telnet.yaml
```

## Copilot workflow

Before implementing a command family, Copilot should:

1. locate its YAML records;
2. read the full `source_text`;
3. identify documented query operations;
4. identify documented mutation operations;
5. obtain real-device output fixtures if parsing behaviour is not sufficiently specified;
6. implement parser tests;
7. implement semantic comparison and command rendering;
8. prove check mode and second-run idempotency before treating it as a resource module.
