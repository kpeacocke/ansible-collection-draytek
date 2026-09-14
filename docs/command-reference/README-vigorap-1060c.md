# DrayTek VigorAP 1060C management evidence catalogue

This package converts the **VigorAP 1060C User's Guide v1.4** for **firmware V1.4.9** into a structured evidence base for GitHub Copilot and Ansible collection design.

## Critical difference from the VigorSwitch catalogue

This manual is **not a CLI reference**. It documents the product primarily through its Web UI and management features. The manual confirms that the Telnet server can be enabled, but it does **not** publish the Telnet command set.

Accordingly, this catalogue deliberately does **not** invent:

- Telnet/SSH command syntax
- Cisco-like commands
- HTTP endpoints
- CGI paths
- form field names
- undocumented APIs
- request/response payloads

The YAML records only what the manual documents: menu paths, settings, values, ranges, defaults, behaviours, prerequisites and source pages.

## Suggested use in an Ansible collection

Treat this file as an **evidence catalogue**, not as an implementation contract.

A sensible implementation sequence is:

1. Establish an actually supported or reverse-engineered transport separately.
2. Add a facts layer first.
3. Implement narrow resources with strong idempotency tests.
4. Keep transport-specific mechanics separate from resource models.
5. Never let Copilot infer device syntax from VigorSwitch, VigorRouter or Cisco IOS examples.

## High-value resource candidates

- `operation_mode`
- `wireless_ssids`
- `wireless_security`
- `wireless_radio_settings`
- `roaming`
- `band_steering`
- `mesh`
- `lan`
- `snmp`
- `ntp`
- `management_services`
- `central_ap_management`
- `radius_server`
- `schedule`

## Provenance

Source: *DrayTek VigorAP 1060C User's Guide*, Version 1.4, Firmware V1.4.9, dated 17 July 2023.

The `source_pages` in each YAML record refer to the printed manual page numbers shown in the guide.

## Repository installation note

The catalogue YAML is unchanged from the supplied package. Copilot instructions have an explicit model scope; 1060C frontmatter has been normalised. The accompanying ZIP matches these installed files. See the validation report for the original archive hash and the limits of this installation review.
