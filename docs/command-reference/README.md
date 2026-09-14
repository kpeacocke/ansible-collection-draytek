# DrayTek Command Evidence Catalogues

This directory contains vendor-derived evidence for device families that the
collection may support in future. These YAML files are design and parser
inputs, not Ansible APIs, runtime configuration, or proof of device support.

```text
docs/command-reference/
  draytek-vigor2927-telnet.yaml
  draytek-vigorswitch-p2100-g2100-telnet.yaml
  draytek-vigorap-1060c-management.yaml
  draytek-vigorap-918r-management.yaml
  draytek-vigorswitch-g1080-management.yaml
```

The catalogue index is [CATALOGUES.md](CATALOGUES.md). It records the device,
firmware/document boundary, evidence type, record count and implementation
limits for each package.

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

## Evidence boundaries

- `telnet` catalogues contain documented CLI syntax, but do not establish SSH
  command parity or safe Ansible semantics.
- `management` catalogues contain Web UI evidence and proposed resource
  mappings, but do not establish HTTP/CGI/API transports.
- Proposed mappings are engineering guidance, not vendor claims.
- No device family is runtime-supported merely because a catalogue exists.
- A resource still needs a read path, sanitised fixtures, comparison logic,
  check-mode behaviour, idempotency proof and device/firmware validation.

The source PDFs retained under `sources/` are provenance for the 918R and G1080
catalogues. Generated ZIP packages and validation logs are intentionally not
kept; their contents are already installed and their checks are represented by
the repository's normal CI and validation commands.

## Recommended repository placement

```text
.github/
  copilot-instructions.md

docs/
  command-reference/
    README.md
    CATALOGUES.md
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
