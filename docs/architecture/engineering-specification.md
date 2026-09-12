# DrayTek Ansible Collection

## Engineering Specification

### Status

Initial implementation specification.

The target quality level is not "working prototype".

The target is:

> A production-quality Ansible network collection whose architecture, behaviour, tests, documentation, security characteristics and maintainability can withstand detailed review by experienced Ansible Networking and Red Hat engineers.

Do not optimise for amount of implemented functionality.

Optimise for correctness, architectural consistency, testability, predictable behaviour and maintainability.

---

# 1. Project Objective

Build an Ansible collection providing first-class automation of DrayTek network devices.

The first supported platform is:

**DrayTek Vigor routers running DrayOS.**

The collection must integrate with normal Ansible networking conventions rather than implementing an isolated SSH scripting framework.

The first implementation must provide:

- native `ansible.netcommon.network_cli` support
- a DrayOS terminal plugin
- a DrayOS cliconf plugin
- arbitrary operational command execution
- structured facts
- generic TR-069 parameter retrieval
- generic TR-069 parameter management
- configuration backup
- declarative resource modules for a deliberately small initial set of DrayOS capabilities
- full check-mode behaviour for configuration modules
- deterministic idempotency
- sanitised errors
- comprehensive tests
- maintained documentation
- CI suitable for an open-source Ansible collection

The architecture must make future support possible for:

- other DrayOS versions
- DrayOS 5
- VigorSwitch
- VigorAP
- VigorACS
- alternative management transports

without requiring existing modules to be rewritten.

---

# 2. Explicit Non-Goals

Do NOT attempt these in the initial implementation:

- browser automation
- HTML scraping
- undocumented HTTP endpoints
- reverse-engineering the DrayTek web UI
- Telnet as the normal management transport
- VigorSwitch support
- VigorAP support
- VigorACS support
- every available DrayOS setting
- opaque execution of arbitrary shell commands on the Ansible controller
- firmware upgrades until device/model validation is implemented
- configuration restore until destructive-operation safeguards are implemented

SSH is the primary interactive transport.

Do not introduce a custom SSH implementation where `ansible.netcommon.network_cli` already provides the required functionality.

---

# 3. Collection Identity

Use a configurable collection namespace during development.

Expected FQCN pattern:

    <namespace>.draytek

Do not assume the project owns:

    draytek.*

    community.*

    redhat.*

or any other third-party Galaxy namespace.

The collection name itself should be:

    draytek

Repository name:

    ansible-collection-draytek

Internal platform name:

    drayos

Expected inventory configuration:

    ansible_connection: ansible.netcommon.network_cli
    ansible_network_os: <namespace>.draytek.drayos

---

# 4. Engineering Principles

All implementation decisions must follow these priorities, in order:

1. correctness
2. predictable Ansible semantics
3. safety
4. idempotency
5. testability
6. backwards compatibility
7. maintainability
8. performance
9. convenience

Do not trade the first six for implementation speed.

---

# 5. Architectural Rule

Separate:

    Ansible module
        ↓
    resource/domain model
        ↓
    DrayOS service layer
        ↓
    command/parameter abstraction
        ↓
    cliconf
        ↓
    network_cli
        ↓
    SSH
        ↓
    device

Modules MUST NOT contain:

- SSH code
- prompt parsing
- CLI login handling
- raw socket handling
- authentication handling
- repeated command parsing logic
- model detection logic duplicated from other modules

The transport and device interaction layers belong in reusable collection plugins and `module_utils`.

---

# 6. Repository Layout

Start with approximately this structure:

    .
    ├── .github/
    │   ├── CODEOWNERS
    │   ├── dependabot.yml
    │   ├── ISSUE_TEMPLATE/
    │   ├── PULL_REQUEST_TEMPLATE.md
    │   └── workflows/
    │       ├── sanity.yml
    │       ├── units.yml
    │       ├── integration.yml
    │       ├── lint.yml
    │       └── build.yml
    │
    ├── changelogs/
    │   ├── config.yaml
    │   └── fragments/
    │
    ├── docs/
    │   ├── platform_drayos.md
    │   ├── supported_devices.md
    │   ├── development.md
    │   ├── testing.md
    │   ├── architecture/
    │   │   ├── README.md
    │   │   └── engineering-specification.md
    │   └── security.md
    │
    ├── meta/
    │   └── runtime.yml
    │
    ├── plugins/
    │   ├── cliconf/
    │   │   └── drayos.py
    │   │
    │   ├── terminal/
    │   │   └── drayos.py
    │   │
    │   ├── doc_fragments/
    │   │   └── drayos.py
    │   │
    │   ├── module_utils/
    │   │   ├── __init__.py
    │   │   └── network/
    │   │       └── drayos/
    │   │           ├── __init__.py
    │   │           ├── connection.py
    │   │           ├── command.py
    │   │           ├── errors.py
    │   │           ├── facts.py
    │   │           ├── models.py
    │   │           ├── parser.py
    │   │           ├── tr069.py
    │   │           ├── validators.py
    │   │           └── resource/
    │   │               ├── __init__.py
    │   │               ├── base.py
    │   │               ├── dns.py
    │   │               ├── hostname.py
    │   │               └── ntp.py
    │   │
    │   └── modules/
    │       ├── drayos_command.py
    │       ├── drayos_facts.py
    │       ├── drayos_tr069.py
    │       ├── drayos_backup.py
    │       ├── drayos_hostname.py
    │       ├── drayos_dns.py
    │       └── drayos_ntp.py
    │
    ├── tests/
    │   ├── fixtures/
    │   │   └── drayos/
    │   ├── integration/
    │   │   └── targets/
    │   └── unit/
    │       └── plugins/
    │           ├── cliconf/
    │           ├── terminal/
    │           ├── module_utils/
    │           └── modules/
    │
    ├── .gitignore
    ├── .gitattributes
    ├── .editorconfig
    ├── CODE_OF_CONDUCT.md
    ├── CONTRIBUTING.md
    ├── LICENSE
    ├── MAINTAINERS.md
    ├── README.md
    ├── SECURITY.md
    ├── galaxy.yml
    ├── pyproject.toml
    └── requirements.yml

Do not create directories merely to make the repository look complete. Every committed directory must have a purpose.

---

# 7. Runtime Dependencies

Use:

    ansible.netcommon

for networking connection infrastructure.

Use:

    ansible.utils

only where it provides a concrete advantage.

Do not vendor functionality already provided by these collections.

Specify dependency minimum versions deliberately in `galaxy.yml`.

Do not use unconstrained dependencies.

The minimum supported `ansible-core` version must be explicitly defined and tested.

Initially target currently maintained ansible-core releases rather than arbitrary historical compatibility.

---

# 8. Python Requirements

Use modern Python.

Requirements:

- `from __future__ import annotations` where appropriate
- type annotations for internal APIs
- small functions
- explicit exceptions
- no blanket `except Exception:` unless re-raising through a well-defined boundary
- no mutable default arguments
- no global mutable state
- no runtime `print`
- no logging of credentials
- no command construction through unsafe interpolation where user input can affect parsing
- no unnecessary third-party runtime dependencies

Prefer Python standard-library functionality where practical.

---

# 9. DrayOS Platform Detection

Implement a single platform identification mechanism.

Return a structured object such as:

    {
        "vendor": "DrayTek",
        "platform": "DrayOS",
        "model": "VigorXXXX",
        "firmware_version": "...",
        "hardware_version": "...",
        "serial_number": "...",
        "capabilities": [...]
    }

Never infer capabilities from the model string alone when capability detection is possible.

The detection implementation must distinguish between:

- supported DrayOS
- unsupported DrayOS variant
- DrayOS 5 if behaviour differs
- VigorSwitch
- VigorAP
- unknown DrayTek platform

Unsupported platforms must fail clearly.

Example:

    UnsupportedPlatformError:
    Detected VigorSwitch Pxxxx. This collection version currently supports
    DrayOS router platforms only.

Do not continue and hope compatible commands work.

---

# 10. Capability Model

Create a capability layer.

Examples:

    Capability.TR069_GET
    Capability.TR069_SET
    Capability.CONFIG_BACKUP
    Capability.REBOOT
    Capability.NTP
    Capability.DNS
    Capability.VLAN
    Capability.FIREWALL
    Capability.VPN
    Capability.WIRELESS

Modules must check required capabilities before performing operations.

Do not scatter firmware/model checks throughout individual modules.

Capability detection should ultimately be driven by:

- platform
- firmware
- available command behaviour
- supported TR-069 parameter tree

where possible.

---

# 11. Terminal Plugin

Implement:

    plugins/terminal/drayos.py

Responsibilities:

- identify DrayOS command prompts
- identify login/password prompts where appropriate
- detect CLI error responses
- disable paging if a documented safe mechanism exists
- handle terminal initialisation
- handle privilege transitions only if DrayOS actually requires them

Prompt regular expressions must:

- be anchored appropriately
- not greedily match arbitrary command output
- be tested against captured fixtures
- support hostname variations
- avoid catastrophic regex behaviour

Every supported prompt form needs a unit test.

Every recognised CLI error form needs a unit test.

Do not invent pager or privilege commands.

Capture behaviour from real devices and add fixtures first.

---

# 12. Cliconf Plugin

Implement:

    plugins/cliconf/drayos.py

This is the primary Ansible networking abstraction for DrayOS.

Support appropriate cliconf operations including:

- `get()`
- command execution
- platform capability reporting
- device info collection

Implement configuration methods only where DrayOS command semantics actually support them safely.

Do not pretend DrayOS has Cisco-style configuration mode if it does not.

The cliconf plugin should expose enough functionality for standard modules such as:

    ansible.netcommon.cli_command

to operate on DrayOS.

This is an important acceptance test.

---

# 13. Connection Utility

Provide a thin collection-specific connection abstraction around Ansible networking APIs.

For example:

    DrayOSConnection

Responsibilities:

- execute one command
- execute ordered command sets
- normalise command results
- translate connection failures
- apply command timeout behaviour
- perform platform discovery
- provide a stable internal interface to modules

The abstraction must NOT create its own SSH connection.

---

# 14. Error Taxonomy

Create explicit internal exceptions.

At minimum:

    DrayTekError
    ConnectionError
    AuthenticationError
    CommandError
    CommandTimeoutError
    ParseError
    UnsupportedPlatformError
    UnsupportedFirmwareError
    UnsupportedCapabilityError
    ValidationError
    TR069Error
    TR069ParameterNotFound
    TR069ReadOnlyParameter
    ConfigurationError

Convert these to useful Ansible failures at the module boundary.

Errors should contain:

- operation
- device/platform information where safe
- command category
- actionable reason

Errors must NOT contain:

- passwords
- tokens
- PSKs
- SNMP communities
- VPN secrets
- complete configurations containing secrets

---

# 15. CLI Command Module

Implement:

    drayos_command

Purpose:

Run operational DrayOS commands.

Parameters should follow normal Ansible networking conventions.

At minimum:

    commands:
    wait_for:
    match:
    retries:
    interval:

where those semantics can reuse established Ansible patterns.

Return:

    changed: false
    stdout:
    stdout_lines:

Command execution alone must never return:

    changed: true

unless the API explicitly represents a mutating operation, and arbitrary mutation should preferably not be exposed through this module.

Document clearly that `drayos_command` is primarily for operational commands and diagnostic escape hatches.

---

# 16. Facts Module

Implement:

    drayos_facts

Return facts under:

    ansible_facts

Use a predictable namespace.

Example categories:

    default
    hardware
    interfaces
    wan
    lan
    system

Initial required facts:

    model
    firmware_version
    hardware_version
    serial_number
    hostname
    uptime
    management information
    available interfaces
    WAN status where supported
    LAN addressing
    capability information

Do not make a single facts call execute dozens of expensive commands unnecessarily.

Support gathering subsets.

Example:

    gather_subset:
      - default
      - interfaces

Facts parsing must be fixture-driven.

Never silently return fabricated defaults when parsing fails.

---

# 17. TR-069 Abstraction

This should be one of the strongest pieces of the collection.

Implement a reusable interface around:

    sys tr069 get
    sys tr069 set

Represent parameters internally as objects rather than loose strings.

Example:

    TR069Parameter(
        path="InternetGatewayDevice....",
        value=...,
        data_type=...,
        writable=...
    )

Required operations:

    get(path)
    get_tree(path)
    set(path, value)
    exists(path)

Potential future operations:

    metadata(path)
    discover(path)

All parsing belongs in:

    module_utils/network/drayos/tr069.py

not modules.

---

# 18. Generic TR-069 Module

Implement:

    drayos_tr069

This module is primarily:

- an expert escape hatch
- a diagnostic tool
- an enabler for unsupported settings

Example:

    - name: Read parameter
      <namespace>.draytek.drayos_tr069:
        path: InternetGatewayDevice.Time.
        state: query

Configuration example:

    - name: Set parameter
      <namespace>.draytek.drayos_tr069:
        path: ...
        value: ...
        state: present

Required semantics:

For reads:

    changed: false

For writes:

1. read current value
2. normalise current value
3. normalise desired value
4. compare
5. write only when different
6. re-read
7. verify final state

Check mode:

1. read current value
2. compare
3. report whether change WOULD occur
4. never execute `set`

Return:

    path
    before
    after
    changed

Never return secret values unless explicitly safe.

Add support for:

    no_log

on sensitive module parameters.

---

# 19. Normalisation

A serious declarative module must not compare raw CLI strings.

Implement canonical normalisation.

Examples:

Boolean inputs:

    true
    1
    yes
    enabled
    Enable

may represent the same device state.

Likewise:

- IPv4 addresses
- IPv6 addresses
- CIDR notation
- integer values
- enumerations
- whitespace
- case-insensitive enums

must be normalised before state comparison where appropriate.

Do not hide meaningful distinctions.

Unit-test every normalisation rule.

---

# 20. Resource Modules

Do not begin by implementing 30 modules.

Start with three comparatively safe resources.

Recommended initial resources:

    drayos_hostname
    drayos_dns
    drayos_ntp

These are enough to prove the design without beginning with dangerous firewall, VPN or WAN changes.

Each resource module must implement declarative state.

Use normal Ansible resource semantics where suitable.

Example:

    - name: Configure DNS
      <namespace>.draytek.drayos_dns:
        config:
          servers:
            - 1.1.1.1
            - 1.0.0.1
        state: merged

Supported state vocabulary should be chosen from standard network resource-module conventions where they make semantic sense:

    merged
    replaced
    overridden
    deleted
    gathered
    parsed
    rendered

Do NOT implement a state merely because Cisco modules expose it.

Each state must have meaningful and deterministic DrayOS semantics.

---

# 21. Resource Module Internal Pattern

Every resource should follow this logical workflow:

    validate desired configuration
            ↓
    discover device/platform/capabilities
            ↓
    gather existing configuration
            ↓
    normalise existing configuration
            ↓
    normalise desired configuration
            ↓
    calculate semantic diff
            ↓
    generate operations
            ↓
    CHECK MODE?
        yes → return proposed changes
        no  → execute
            ↓
    gather state again
            ↓
    verify resulting state
            ↓
    return result

Never determine success simply because a command returned without an obvious error.

---

# 22. Idempotency Requirement

This is mandatory.

For every configuration module:

First execution:

    changed: true

Immediate identical second execution:

    changed: false

A module which sends commands every time but returns `changed: false` is NOT idempotent.

A module which blindly writes configuration every time is NOT acceptable.

Tests must explicitly demonstrate second-run idempotency.

---

# 23. Check Mode

Every declarative module must support:

    supports_check_mode=True

Check mode MUST:

- connect to the device
- gather existing state
- validate inputs
- calculate the proposed delta
- return the expected `changed` state
- perform zero mutations

Check mode cannot simply return without doing anything.

---

# 24. Diff Mode

Where meaningful, support Ansible diff mode.

Return a structured before/after representation.

Example:

    before:
      servers:
        - 192.0.2.53

    after:
      servers:
        - 1.1.1.1
        - 1.0.0.1

Do not expose secret fields in diffs.

Sensitive values should be represented as:

    VALUE_SPECIFIED_IN_NO_LOG_PARAMETER

or another established Ansible-compatible redaction mechanism.

---

# 25. Backup Module

Implement:

    drayos_backup

The module must retrieve a native DrayOS configuration backup using a supported mechanism.

Do not scrape a browser download workflow.

If a supported machine-accessible backup interface cannot be confirmed for a target firmware family, report the feature as unsupported rather than inventing one.

Required behaviour:

    backup:
      filename
      path
      checksum
      model
      firmware_version
      timestamp

Checksum:

    SHA-256

Security:

- use restrictive file permissions
- do not log backup contents
- document that backups contain sensitive configuration
- fail if destination handling is unsafe
- never commit fixtures containing real customer credentials

---

# 26. Dangerous Operations

Future modules performing any of the following:

- reboot
- WAN changes
- default-route changes
- firmware upgrade
- configuration restore
- factory reset
- management-interface changes

must have additional safeguards.

At minimum:

- explicit requested state
- model validation
- firmware validation where relevant
- deterministic pre-checks
- unambiguous documentation
- integration tests
- no accidental execution from defaults

Factory reset must never be part of a generic configuration module.

---

# 27. Secret Handling

Treat the following as secrets:

- administrator passwords
- PPP credentials
- VPN credentials
- VPN PSKs
- wireless PSKs
- certificate private keys
- TR-069 credentials
- SNMP communities where appropriate
- API credentials
- backup passwords

Any module parameter carrying these must use:

    no_log=True

Never include secrets in:

- errors
- debug logs
- returned diffs
- fixtures
- example inventory
- recorded integration-test output

---

# 28. SSH Security

Default to SSH.

Do not recommend Telnet except in explicit legacy documentation.

Do not globally disable SSH host-key checking in examples.

Documentation should demonstrate known-host management rather than:

    ansible_host_key_checking=false

as the production default.

Passwords must not be embedded in inventory examples.

Use:

- Ansible Vault
- AAP credentials
- environment/injected credential mechanisms

as examples.

---

# 29. Input Validation

Use `argument_spec` comprehensively.

Validation must reject invalid configuration before device mutation.

Use:

- choices
- required_if
- required_by
- mutually_exclusive
- required_together

where appropriate.

Additional validators should handle:

- IPv4
- IPv6
- subnet masks
- CIDRs
- DNS servers
- ports
- VLAN IDs
- hostname syntax
- interface identifiers
- allowed parameter values

Never silently truncate or coerce clearly invalid data.

---

# 30. Documentation Contract

Every module must contain valid:

    DOCUMENTATION
    EXAMPLES
    RETURN

Documentation and argument specification must agree exactly.

Every option must document:

- type
- default
- requirement
- behaviour
- version introduced where applicable
- security implications where applicable

Examples must use FQCNs.

Examples must be executable apart from placeholder inventory values.

Avoid fake capabilities.

If a feature is model-dependent, say so.

---

# 31. Platform Documentation

Create:

    docs/platform_drayos.md

Cover:

- supported connection type
- `ansible_connection`
- `ansible_network_os`
- SSH configuration
- host-key checking
- privilege requirements
- tested models
- tested firmware
- limitations
- troubleshooting
- command timeout settings
- unsupported device families

Example inventory:

    all:
      children:
        draytek:
          hosts:
            branch-router-01:
              ansible_host: 192.0.2.10
              ansible_user: automation
              ansible_connection: ansible.netcommon.network_cli
              ansible_network_os: <namespace>.draytek.drayos

Do not include plaintext passwords.

---

# 32. Supported Device Matrix

Maintain:

    docs/supported_devices.md

Use a table containing:

    Product
    Platform
    Firmware
    Tested
    CI Tested
    Support Level
    Notes

Distinguish:

    Supported

    Tested

    Expected compatible

These terms are not interchangeable.

Never claim that an entire Vigor family works because one model passed tests.

---

# 33. Fixtures

Captured CLI interactions are important test assets.

Store sanitised fixtures under:

    tests/fixtures/drayos/

Example:

    vigor2866/
        4.x/
            system_status.txt
            tr069_time.txt

Fixtures must:

- identify model and firmware
- contain no credentials
- contain no public customer IP addresses
- contain no serial numbers from production equipment
- preserve real CLI formatting

Do not "clean up" whitespace that the parser actually encounters.

---

# 34. Parser Design

Parsers must be:

- pure where possible
- independent of SSH
- deterministic
- fixture-driven

Example:

    parse_system_status(text: str) -> SystemInformation

A parser should not make device calls.

Do not combine:

    fetch + parse + mutate

in one large function.

Malformed unexpected input must raise a controlled parse error rather than returning plausible but incorrect data.

---

# 35. Unit Tests

Use pytest through `ansible-test`.

Unit-test:

- terminal prompt recognition
- CLI error recognition
- platform detection
- firmware parsing
- facts parsing
- TR-069 parsing
- TR-069 normalisation
- parameter comparison
- validators
- capability detection
- resource diff calculation
- command generation
- secret redaction
- module argument validation
- check-mode behaviour
- success paths
- failure paths

Tests should focus on behaviour, not implementation trivia.

---

# 36. Integration Tests

Create Ansible integration tests under:

    tests/integration/targets/

Required initial targets:

    drayos_command
    drayos_facts
    drayos_tr069
    drayos_hostname
    drayos_dns
    drayos_ntp

Where hardware cannot run in public CI, separate:

1. deterministic CI tests using mocked/captured device interfaces
2. hardware integration tests triggered manually or in an internal runner

Document this distinction.

Never pretend mocked tests are hardware integration tests.

---

# 37. State Tests

Every resource module requires these scenarios:

### Create/change

Existing state differs.

Expect:

    changed: true

### Idempotent second execution

Existing state equals desired state.

Expect:

    changed: false

and zero configuration commands.

### Check mode change

State differs.

Expect:

    changed: true

and zero writes.

### Check mode identical

State matches.

Expect:

    changed: false

and zero writes.

### Device rejects command

Expect:

    failed: true

with sanitised actionable error.

### Verification fails

Command appears successful but resulting state is wrong.

Expect:

    failed: true

Do not report successful configuration.

---

# 38. Failure Injection

Add tests deliberately simulating:

- connection timeout
- authentication failure
- malformed prompt
- unexpected CLI response
- truncated response
- unsupported model
- unsupported firmware
- missing TR-069 parameter
- read-only TR-069 parameter
- command rejection
- command timeout
- connection loss after mutation
- changed output format
- verification mismatch

A robust collection is defined as much by controlled failure as successful operation.

---

# 39. Sanity Tests

CI must run:

    ansible-test sanity --docker

No blanket skips.

Do not add entries to sanity ignore files simply to make CI green.

Every exception must:

- be narrowly scoped
- contain justification
- preferably reference an upstream compatibility issue

The target is zero collection-specific sanity exclusions.

---

# 40. Unit Test CI

Run:

    ansible-test units --docker

against each supported ansible-core/Python combination where practical.

Do not claim support for a runtime combination that CI never exercises.

---

# 41. Build Validation

CI must run:

    ansible-galaxy collection build

Then install the generated tarball into a clean environment.

Run a smoke test against the installed artefact.

This catches packaging mistakes hidden by source-tree execution.

---

# 42. Documentation Validation

CI must validate:

- module docs render
- argument specs match documentation
- links are valid where practical
- examples parse as YAML
- collection builds without undocumented plugin failures

Use `ansible-test sanity` documentation validators rather than inventing replacements.

---

# 43. Linting

Use:

    ansible-lint

where appropriate.

Python tooling may additionally use:

    ruff

if it adds value.

Do not allow formatter/linter configuration to conflict with Ansible sanity requirements.

Ansible sanity is authoritative for collection compliance.

---

# 44. Coverage

Coverage percentage is not the primary quality metric.

However:

- critical parsers
- diff engines
- normalisers
- command generators
- validation code

should have strong unit coverage.

Do not add meaningless tests solely to increase a percentage.

---

# 45. GitHub Pull Request Gate

A pull request may not merge unless:

- sanity passes
- units pass
- integration simulation passes
- lint passes
- build succeeds
- documentation validates
- no generated artefact unexpectedly changes
- changelog fragment exists when appropriate

Use branch protection assumptions in repository documentation.

---

# 46. Changelog

Use Ansible collection changelog fragments.

Categorise changes such as:

    major_changes
    minor_changes
    breaking_changes
    deprecated_features
    removed_features
    security_fixes
    bugfixes
    known_issues

Do not maintain release history manually in README.

---

# 47. Semantic Versioning

Use SemVer.

During initial development:

    0.x

Once API and module contracts are considered stable:

    1.0.0

Breaking module parameter behaviour requires a major-version process once 1.x is released unless an established Ansible deprecation mechanism applies.

---

# 48. Compatibility Policy

Do not promise indefinite compatibility.

Maintain a documented compatibility matrix for:

- collection version
- ansible-core version
- Python version
- DrayOS firmware
- device model

When firmware changes CLI formatting, add a fixture and parser test before modifying shared parsing.

Do not fix one model by breaking another.

---

# 49. Public API Stability

Treat as public API:

- module names
- module arguments
- documented return values
- FQCNs
- supported resource states
- facts structure

Treat internal `module_utils` as internal unless documented otherwise.

Do not unnecessarily expose internal Python classes as public API.

---

# 50. Naming

Modules:

    drayos_command
    drayos_facts
    drayos_tr069
    drayos_backup
    drayos_hostname
    drayos_dns
    drayos_ntp

Future modules should describe a resource, not an action.

Prefer:

    drayos_firewall_rule

over:

    drayos_set_firewall

Declarative modules describe desired state.

---

# 51. No Giant "Configure Everything" Module

Do not create:

    drayos_config:
        hostname:
        lan:
        wan:
        dns:
        vlan:
        firewall:
        vpn:
        wifi:
        ...

That becomes impossible to reason about, test and evolve safely.

Resource boundaries must remain explicit.

---

# 52. No Generic Dictionary Dumping

Do not create a supposedly declarative module taking:

    settings:
      arbitrary_key: arbitrary_value

except for the explicitly low-level `drayos_tr069` expert interface.

High-level modules require typed schemas.

This is the distinction between a useful collection and a remote scripting API.

---

# 53. Command Generation

Command generation should be independently testable.

Example conceptual interface:

    operations = DNSResource.plan(current, desired)

Producing:

    [
        Operation(
            parameter="...",
            before="192.0.2.53",
            after="1.1.1.1"
        )
    ]

Then:

    operations.render()

or an equivalent explicit mechanism.

Do not mix comparison logic and network mutation.

---

# 54. Transactions and Partial Failure

Assume multi-setting changes can partially succeed.

For each multi-operation resource:

- preserve the planned operation list
- execute deterministically
- stop appropriately on error
- re-read final state
- report what happened
- never claim atomicity if DrayOS provides none

Example error should explain:

    2 of 3 requested parameter changes were applied before the device rejected
    the third operation. Current state was re-read. See result.current.

Do not automatically roll back unless the platform provides reliable rollback semantics and they are explicitly implemented.

Fake rollback is worse than partial-state reporting.

---

# 55. Verification

Configuration mutation must use:

    read
    compare
    write
    re-read
    verify

where practical.

Do not rely solely on command acknowledgements.

A device returning success while retaining the old value must fail verification.

---

# 56. Reboot Detection

Some configuration may require reboot or service restart.

Represent this explicitly.

Potential result:

    reboot_required: true

Do not automatically reboot unless the module's contract explicitly states that it may.

Configuration modules should generally leave reboot orchestration to the playbook.

---

# 57. Fact Schema

Define internal typed models.

For example:

    DeviceInfo
    InterfaceInfo
    WANInfo
    LANInfo
    FirmwareInfo
    CapabilitySet

Do not pass loosely structured nested dictionaries throughout the code base.

Convert models into Ansible dictionaries at the module boundary.

---

# 58. Model/Firmware Quirks

Centralise quirks.

Potential pattern:

    compatibility/
        base.py
        drayos4.py
        drayos5.py

or an equivalent design.

Avoid code such as:

    if model == "2866":
        ...
    elif model == "2927":
        ...

spread through dozens of modules.

Model-specific workarounds require:

- documented reason
- fixture
- test

---

# 59. Telemetry and Logging

Do not add application telemetry.

Debug output may be available through Ansible verbosity.

Never send usage information outside the control node.

Never log credentials.

Do not leave raw SSH transcripts enabled by default because they may contain secrets.

---

# 60. Security Documentation

Create:

    SECURITY.md

and:

    docs/security.md

Document:

- how to report vulnerabilities
- credential handling
- backup sensitivity
- SSH host-key expectations
- risks of management exposure
- use of least-privileged management accounts where possible
- sensitive module fields
- fixture sanitisation policy

---

# 61. Supply-Chain Hygiene

GitHub Actions:

- use maintained actions
- pin important actions appropriately
- minimise workflow permissions
- use `permissions:` explicitly
- do not expose repository secrets to untrusted PR code
- avoid arbitrary curl-pipe-shell installation
- use Dependabot or equivalent for workflow dependencies

Generated release artefacts must be reproducible enough to investigate their origin.

---

# 62. Development Documentation

Create:

    docs/development.md

Include:

    python environment
    collection path
    dependency installation
    sanity testing
    unit testing
    integration testing
    local hardware testing
    fixture generation
    documentation generation
    collection build

A new contributor should not need tribal knowledge to run the test suite.

---

# 63. Test Device Safety

Hardware integration testing must never assume production hardware.

Introduce an explicit environment variable or inventory designation for destructive tests.

Example conceptual grouping:

    drayos_test_safe
    drayos_test_disruptive

Normal CI or developer test execution must not reboot or reset equipment.

---

# 64. Source Documentation

Every unusual DrayOS behaviour implemented in code should reference its source in comments or architecture documentation.

Source precedence:

1. official DrayTek documentation
2. observed behaviour on identified firmware/model
3. community reports

Do not convert internet folklore into supported collection behaviour without validation.

---

# 65. Discovery Before Implementation

Before implementing each resource module:

1. identify relevant official DrayTek documentation
2. identify corresponding CLI/TR-069 representation
3. capture output from a real test device
4. determine read behaviour
5. determine write behaviour
6. determine normalisation
7. determine error output
8. determine whether restart/reboot is required
9. add fixtures
10. add parser tests
11. only then implement mutation

Never implement a write operation from undocumented assumptions.

---

# 66. First Development Milestone

Milestone 1 is connectivity, not configuration.

Deliver:

    terminal plugin
    cliconf plugin
    platform detection
    drayos_command

Acceptance test:

A normal inventory using:

    ansible_connection: ansible.netcommon.network_cli
    ansible_network_os: <namespace>.draytek.drayos

can successfully run:

    ansible.netcommon.cli_command

against a supported Vigor router.

Do not begin resource modules until this works reliably.

---

# 67. Second Development Milestone

Deliver:

    structured device model
    facts parser
    capability detection
    drayos_facts

Acceptance criteria:

- facts are deterministic
- malformed fixture handling is tested
- multiple firmware fixtures are represented
- no configuration mutation occurs

---

# 68. Third Development Milestone

Deliver:

    TR-069 parser
    TR-069 client/service abstraction
    drayos_tr069

Acceptance criteria:

- get single parameter
- get subtree
- compare values
- set changed parameter
- idempotent second execution
- check mode
- verify after setting
- controlled unsupported/read-only errors

This is the architectural foundation for most later resource modules.

---

# 69. Fourth Development Milestone

Deliver:

    drayos_hostname
    drayos_dns
    drayos_ntp

Each must use the common resource workflow.

No resource-specific SSH or CLI framework code may appear in these modules.

---

# 70. Fifth Development Milestone

Deliver configuration backup only after a supported machine interface has been validated.

Then evaluate resources in roughly this order:

    LAN
    static routes
    VLAN
    DHCP
    SNMP
    users
    NAT
    firewall objects
    firewall rules
    VPN

Do not jump directly to firewall/VPN because they are interesting.

The simpler modules prove that the state architecture is correct.

---

# 71. Future VigorSwitch Support

Do not force VigorSwitch into DrayOS abstractions.

Future platform:

    vigorswitch

Potential inventory:

    ansible_network_os: <namespace>.draytek.vigorswitch

It should receive its own:

    terminal plugin
    cliconf plugin
    platform services
    parsers
    fixtures
    modules where semantics differ

Reusable generic components may live above both.

---

# 72. Future VigorAP Support

Likewise:

    vigorap

must have its own platform contract if its management interface materially differs.

Do not hide platform differences behind dozens of conditionals.

---

# 73. Future VigorACS Integration

VigorACS is a separate management-plane integration.

It should eventually be treated as a separate transport/service implementation.

Potential future architecture:

    resource module
         ↓
    DrayTek device abstraction
         ↓
      ┌──────────────┐
      │              │
    Direct SSH     VigorACS
      │              │
    DrayOS         TR-069
      │              │
      └──── device ──┘

Do not put VigorACS-specific concepts into the initial SSH transport.

---

# 74. README

README must include:

- what the collection does
- current scope
- supported platforms
- installation
- dependencies
- quick-start inventory
- quick-start playbook
- links to platform docs
- testing
- contributing
- support policy
- licence

The first paragraph must make clear:

> Initial releases support DrayTek Vigor routers running DrayOS. VigorSwitch,
> VigorAP and VigorACS are not yet supported unless explicitly listed in the
> supported-device matrix.

---

# 75. Code Review Standard

Before considering any feature complete, review it using these questions.

### Architecture

- Is transport logic duplicated?
- Is platform-specific behaviour correctly isolated?
- Is there an unnecessary abstraction?
- Is there a missing abstraction?

### Ansible semantics

- Is `changed` correct?
- Is check mode real?
- Is diff mode safe?
- Does the argument spec match docs?
- Does the return structure follow Ansible conventions?

### Device semantics

- Is current state actually gathered?
- Are values normalised?
- Is device state verified after mutation?
- Are firmware differences handled deliberately?

### Security

- Could a secret appear in an exception?
- Could a secret appear in diff output?
- Does any example encourage unsafe SSH configuration?
- Can user input result in unintended command execution?

### Testing

- Happy path?
- Idempotency?
- Check mode?
- Parser failure?
- Device rejection?
- Connection failure?
- Verification failure?
- Unsupported firmware?

### Maintainability

- Could a second DrayOS model be added without rewriting this?
- Could a changed output fixture expose a parser regression?
- Is unusual behaviour documented?

A "yes, but it works on my router" response is not sufficient.

---

# 76. Definition of Done for a Module

A module is NOT done because it works manually.

A module is done only when:

- implementation exists
- argument spec is complete
- DOCUMENTATION is complete
- EXAMPLES are complete
- RETURN is complete
- unit tests exist
- idempotency test exists
- check-mode test exists
- failure-path tests exist
- relevant fixture exists
- integration test exists or documented hardware-test reason exists
- sanity passes
- lint passes
- secrets are redacted
- documentation identifies model/firmware constraints
- changelog fragment exists
- collection builds successfully

---

# 77. Definition of Done for v0.1.0

Version 0.1.0 requires:

### Platform

- DrayOS terminal plugin
- DrayOS cliconf plugin
- reliable SSH/network_cli operation

### Modules

- `drayos_command`
- `drayos_facts`
- `drayos_tr069`
- `drayos_hostname`
- `drayos_dns`
- `drayos_ntp`

### Engineering

- complete unit suite
- representative integration suite
- hardware validation against at least one documented DrayOS model
- captured sanitised fixtures
- sanity clean
- build clean
- CI clean
- complete README
- platform guide
- supported-device matrix
- contribution guide
- security policy
- changelog framework

Do not expand v0.1.0 merely because additional modules seem easy.

Ship the architecture first.

---

# 78. Copilot Working Instructions

When implementing this repository:

1. Read this specification completely before changing code.
2. Read existing architecture and tests before adding a feature.
3. Do not infer undocumented DrayTek CLI syntax.
4. Do not invent API endpoints.
5. Do not use browser scraping.
6. Do not bypass `ansible.netcommon` networking infrastructure.
7. Prefer extending common utilities over copying code between modules.
8. Write or update tests with every behavioural change.
9. Run relevant unit tests after each implementation step.
10. Run full sanity and test suites before declaring work complete.
11. Do not disable failing tests to complete a task.
12. Do not weaken assertions merely because implementation differs.
13. Do not introduce backwards-incompatible behaviour silently.
14. Never place real credentials or production configuration in fixtures.
15. When required DrayTek behaviour is unknown, stop that feature and record exactly what device evidence or documentation is missing.
16. Do not substitute guessed behaviour for missing evidence.
17. Keep pull requests small and cohesive.
18. Prefer the smallest complete implementation over speculative extensibility.

---

# 79. Copilot Implementation Workflow

For every issue:

## Step 1 — Restate the contract

Write down:

- expected input
- current device state
- desired state
- expected output
- mutation behaviour
- check-mode behaviour
- failure behaviour

## Step 2 — Identify architecture

Determine whether the change belongs in:

    terminal
    cliconf
    module
    module_utils
    parser
    resource model
    documentation

Do not default everything into the module.

## Step 3 — Tests first where practical

Add:

- parser fixtures
- normalisation tests
- diff tests
- failure tests

## Step 4 — Implement minimum behaviour

Do not add adjacent functionality not required by the issue.

## Step 5 — Verify

Run:

    ansible-test sanity --docker
    ansible-test units --docker

plus relevant integration tests.

## Step 6 — Review the diff

Specifically search for:

    TODO
    FIXME
    print(
    except Exception
    no_log
    password
    secret
    token
    subprocess
    shell=True

Investigate every relevant occurrence.

## Step 7 — Documentation

Update user-facing docs and changelog if behaviour changed.

---

# 80. Architectural Test

The collection architecture is successful if a future engineer can implement:

    drayos_snmp

without needing to understand:

- SSH negotiation
- prompt handling
- authentication
- raw TR-069 output parsing
- platform detection internals

They should need to understand:

- the SNMP resource schema
- how DrayOS represents SNMP state
- how to translate between that state and the collection's internal resource model

That separation is the design objective.

---

# 81. Review Threshold

Before presenting the project for serious external review, assume reviewers will actively look for:

- accidental non-idempotency
- inaccurate `changed` status
- fake check mode
- brittle regex
- swallowed exceptions
- duplicated connection code
- insufficient secret handling
- undocumented model assumptions
- weak fixtures
- tests that only cover happy paths
- argument/documentation mismatch
- custom implementations of existing `ansible.netcommon` functionality
- unsafe defaults
- poor compatibility boundaries
- giant modules
- invented device behaviour

Design the implementation so those criticisms are difficult to make.

---

# 82. Final Constraint

Do not optimise the repository for a demo.

Optimise it so that six months later another network automation engineer can:

1. understand why the architecture exists,
2. reproduce its tests,
3. add another supported DrayOS resource,
4. identify which firmware was validated,
5. diagnose a parser regression from a fixture,
6. determine whether a change is safe,
7. review the pull request without access to the original author.

That is the standard for this project.