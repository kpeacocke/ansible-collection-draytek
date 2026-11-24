# Security policy

## Reporting a vulnerability

Do not report suspected vulnerabilities through a public issue.

Use GitHub private vulnerability reporting when enabled for this repository, or contact the repository owner through the organisation's approved private security channel.

Include the affected version/commit, reproduction details, security impact, and any known mitigations. Do not include live credentials, personal data, or unnecessary sensitive information.

## Credential management

- Supply device SSH credentials through a credential store (for example an AWX machine credential or Ansible Vault), never in inventory, vars files, playbooks, or fixtures.
- The device account used for automation is an administrative CLI account; DrayOS offers no privilege separation on the CLI, so restrict who can use the credential rather than relying on device-side limits.
- Rotate device credentials if they may have appeared in any job output or log.

## Host-key verification

Verify and pin each device's SSH host key out of band before first use. Running with host-key checking disabled is outside this collection's support contract; the recorded live validation used verified host keys and fail-closed SSH policies.

## Sensitive output

- Facts and reads can contain hostnames, serial numbers, internal addresses, DHCP client identifiers, NAT rules, and TR-069 parameter values. Use task-level `no_log: true` where that data must not appear in job output, keep persistent command logging disabled, and review any fact-caching configuration.
- `drayos_tr069` refuses to run without task-level `no_log: true`. Private reads are refused while persistent command logging is enabled.
- Module failures deliberately suppress raw device output. Do not weaken this when debugging against shared infrastructure.

## Privilege requirements and privileged operations

- `drayos_command` sends operator-supplied commands and does not prevent configuration changes in normal mode; in check mode only commands whose first word is `show` are accepted.
- Configuration writes exist only in specific modules with exact platform guards, mandatory readback, and fail-closed verification. There is no generic configuration push path.
- The design details are in the [security architecture](docs/security.md).

## Support and compatibility boundaries

Security claims apply only to the validated combinations in the [device matrix](docs/supported_devices.md) and the [qualification matrix](docs/qualification-matrix.md). Other devices, firmware, transports, and Ansible versions are unverified; do not assume the same guards hold there.
