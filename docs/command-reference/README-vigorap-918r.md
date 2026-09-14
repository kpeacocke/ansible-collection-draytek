# VigorAP 918R management evidence catalogue

This package documents management evidence, not an executable Ansible collection or a CLI reference. It is based on the attached DrayTek VigorAP 918R Series User's Guide v1.6, firmware V1.4.6, dated 5 July 2023 (183 PDF pages). It does not establish support on other firmware, AP models or current mobile-app releases.

## Install

Extract the ZIP into the collection repository root. Its entries begin with `docs/` and `.github/`, so no extra parent directory must be moved. Preserve existing global Copilot instructions. The YAML belongs in documentation, not runtime plugins.

- `docs/command-reference/draytek-vigorap-918r-management.yaml`: structured evidence and separately labelled proposals.
- `docs/command-reference/README-vigorap-918r.md`: scope, conventions and implementation boundaries.
- `.github/instructions/vigorap-918r.instructions.md`: scoped Copilot instructions.
- `docs/command-reference/VALIDATION-vigorap-918r.txt`: actual checks and limitations.

## Reading the YAML

Every record has a stable `id`, a `manual_evidence` object and a `proposed_ansible_mapping` object. Menu paths are ordered display labels, not URLs. Combined `Wireless LAN (2.4GHz/5GHz)` paths summarize parallel menus; explicit band restrictions take precedence. Some inner path components are page sections or dialogs, not sidebar items.

`manual_evidence` contains section and source pages, settings, documented defaults/ranges, constraints, prerequisites, behaviors and uncertainty notes. Each setting inherits the record's source-page list. `null` means not established in the cited evidence; it does not mean disabled, unlimited, absent or optional. Empty lists mean no detail was transcribed for that category, not that no constraints exist. Numeric bounds are not filled in from general networking knowledge. Dropdown options may be partial where the notes say so. Sensitive fields are flagged for handling, not populated with credentials.

Printed Arabic page numbers and physical PDF page numbers are both recorded. Printed p1 is PDF p9; add eight throughout the numbered body. The document identity is on PDF p2. The source SHA-256 identifies the exact attached PDF; the PDF itself is not included in the ZIP.

`proposed_ansible_mapping` is engineering interpretation, not vendor evidence. Resource names are illustrative model-specific candidates, not real modules or an API promise. Operation classes distinguish facts candidates, configuration, active diagnostics, workflows, credentials, backup/restore and disruptive operations. Transport/readback remain null; check mode and idempotency are explicitly unestablished. Implementations must first validate a transport and demonstrate readback, comparison and verification. A facts candidate does not authorize every button on its page.

## Coverage and 918R-specific evidence

The catalogue covers initial access, operation modes, WLAN/security/WDS, client controls, mesh, range extension, LAN/DHCP/portal, system maintenance, Central AP Management, mobile-device controls, RADIUS/certificates, schedules, objects, the mobile app and diagnostics.

| Required feature | Record | Printed pages |
| --- | --- | --- |
| Bandwidth Management | `bandwidth_management` | 52-53; 55 |
| Apple iOS Keep Alive | `apple_ios_keep_alive` | 134-135 |
| Sensor / USB thermometer | `sensor` | 136-137; alert prerequisites 104-105 |
| Speed Test | `speed_test` | 161 |
| Interference Monitor | `interference_monitor` | 165-166 |
| Overload Management | `overload_management` | 115-116 |
| Status of Settings | `status_of_settings` | 116 |
| DrayTek Wireless mobile app | `mobile_app_*` | 144-158 |

Bandwidth limits and Airtime Fairness are mutually exclusive (p55). Mesh supports one root plus up to seven nodes and three wireless hops (pp70-71); the suggestion to use no more than two hops is guidance, not the hard limit. MDM Policies automatically reboots the AP after OK (p125). Configuration backup excludes certificates (p103). Central AP Management overload lists are distinct from WLAN access-control lists.

Status of Settings observes router-side load balancing; it does not provide AP-local controls for those settings. An X means disabled **or** unregistered (p116). Apple iOS keep-alive uses UDP port 5353 every five seconds; the manual does not expose these as editable fields (pp134-135). Sensor prose mentions internal/2.4GHz temperatures, USB thermometers and humidity fields, but does not prove accessory compatibility or built-in humidity hardware on every variant. Verify the physical device before implementation.

## Evidence boundaries

The manual says settings are configured through Web UI (p15) and independently confirms a Telnet CLI enablement control (p108). It supplies no CLI command set. No CLI syntax, CGI path, HTTP configuration endpoint, request payload, mobile API, SNMP OID or TR-069 parameter tree has been invented here. Service configuration does not prove writable automation support. Do not borrow transport details from Vigor2927, VigorSwitch or VigorAP 1060C.

The 1060C conversation describes a 46-record package, but its generated files were unavailable. This is equivalent in requested layout and evidence/proposal separation, not a claimed byte-compatible schema clone. The 918R manual was independently extracted and reviewed.

This is a section-level catalogue, not a full transcription of screenshot-only fields. Mesh Support List, Mesh Syslog, Station Control List, Alert Event and RD-only statistics retain explicit limits rather than guessed schemas. Speed Test/System Log and sensor examples were visually checked. Displayed sample values are not promoted to defaults.

The source has inconsistencies: factory password is described as null on p173 but admin/admin on p15; band-steering text refers to 920RP; some sections use router/WAN wording; the security table repeats and mixes descriptions; sensor navigation labels vary. These are recorded as unresolved, not silently corrected into device behavior. Neither default credential statement is an automatic login fallback.

## Before implementing a proposal

Validate exact hardware/firmware and authorization; obtain vendor transport documentation or controlled lab evidence; record read and write operations independently; build real sanitized response fixtures; compare current and desired state; mutate only when needed; verify resulting state. Establish secret redaction, error handling, session expiry and connection recovery. Prove check mode without changes and prove a second identical run produces no change before claiming support. Treat reboot/reset/upgrade, certificate replacement, mesh synchronization and active diagnostics according to their side effects.

Validation here proves package structure and evidence bookkeeping. It does not prove device behavior, idempotency, check mode, transport support or exhaustive screenshot coverage.
