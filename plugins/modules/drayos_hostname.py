# Copyright: (c) 2026, kpeacocke
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: drayos_hostname
short_description: Gather or configure a DrayOS router hostname
description:
  - Gather or parse the router hostname, or configure it with readback verification.
  - Uses C(sys version) for reads and the vendor-documented C(sys name) command
    for configuration. Does not use TR-069 or a separate configuration mode.
  - Configuration is initially limited to Vigor2927Lac firmware 4.5.2.2.
    State transitions are offline-tested, not hardware-write-qualified.
version_added: "0.1.0"
author:
  - kpeacocke (@kpeacocke)
options:
  config:
    description: Desired hostname. Required and accepted only with V(merged).
    type: dict
    suboptions:
      hostname:
        description:
          - Router name, compared case-sensitively without rewriting the desired value.
          - Accepts 1-39 ASCII letters, digits, dots, underscores or hyphens,
            beginning with a letter or digit. This is a conservative module policy,
            not a claim about all firmware CLI limits.
        type: str
        required: true
  state:
    description:
      - V(merged) compares, writes only on difference, then rereads and verifies.
      - V(gathered) reads the current hostname without writes.
      - V(parsed) parses O(running_config) without connecting to a device.
    type: str
    choices: [merged, gathered, parsed]
    default: merged
  running_config:
    description: Complete C(sys version) output. Required and accepted only with V(parsed).
    type: str
notes:
  - Requires C(ansible.netcommon.network_cli), except in V(parsed) state.
  - Requires C(ansible_network_single_user_mode=false), the default.
    DrayOS command caching is unsupported and is rejected before execution.
  - Check mode reads and predicts changes without writing. Diff mode returns
    only the hostname, never the full C(sys version) output.
  - A failed write or verification may leave a changed device. Such failures
    report C(changed=true), meaning that a change may have occurred, not that
    the desired state was verified. No automatic rollback or retry is attempted.
  - Does not reboot, save a configuration separately, or claim persistence
    across reboot. Establish an approved recovery plan before write testing.
attributes:
  check_mode:
    support: full
  diff_mode:
    support: full
"""

EXAMPLES = r"""
- name: Gather the router hostname
  kpeacocke.draytek.drayos_hostname:
    state: gathered

- name: Predict a hostname change without writing
  kpeacocke.draytek.drayos_hostname:
    config:
      hostname: branch-router
    state: merged
  check_mode: true
  diff: true

- name: Configure hostname on an authorised test router
  kpeacocke.draytek.drayos_hostname:
    config:
      hostname: branch-router
    state: merged
"""

RETURN = r"""
gathered:
  description: Current hostname in V(gathered) state.
  returned: when state is gathered
  type: dict
parsed:
  description: Hostname extracted from O(running_config).
  returned: when state is parsed
  type: dict
before:
  description: Hostname observed before configuration.
  returned: when state is merged and successful
  type: dict
after:
  description: Verified hostname, or predicted hostname in check mode.
  returned: when state is merged and successful
  type: dict
commands:
  description: Configuration commands executed, or planned in check mode.
  returned: when state is merged and successful
  type: list
  elements: str
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.connection import (
    run_commands,
)
from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.errors import (
    CommandError,
    ConnectionError as DrayOSConnectionError,
    DrayTekError,
    ParseError,
    VerificationError,
)
from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.hostname import (
    build_hostname_command,
    parse_hostname,
    validate_hostname_platform,
)


def read_hostname(module: AnsibleModule) -> tuple[str, dict[str, str]]:
    responses = run_commands(module, ["sys version"])
    if not isinstance(responses, list) or len(responses) != 1 or not isinstance(responses[0], str):
        raise ParseError("Expected exactly one text response to sys version")
    return responses[0], parse_hostname(responses[0])


def main() -> None:
    module = AnsibleModule(
        argument_spec={
            "config": {"type": "dict", "options": {
                "hostname": {"type": "str", "required": True},
            }},
            "state": {"type": "str", "choices": ["merged", "gathered", "parsed"],
                      "default": "merged"},
            "running_config": {"type": "str", "no_log": True},
        },
        required_if=[("state", "merged", ["config"]),
                     ("state", "parsed", ["running_config"])],
        supports_check_mode=True,
    )
    state = module.params["state"]
    if module.params["config"] is not None and state != "merged":
        module.fail_json(msg="config is accepted only with state=merged")
    if module.params["running_config"] is not None and state != "parsed":
        module.fail_json(msg="running_config is accepted only with state=parsed")

    write_attempted = False
    phase = "validation"
    try:
        if state == "parsed":
            module.exit_json(changed=False, parsed=parse_hostname(module.params["running_config"]))

        desired = module.params["config"]
        command = build_hostname_command(desired["hostname"]) if desired is not None else None
        phase = "gather"
        raw, before = read_hostname(module)
        if state == "gathered":
            module.exit_json(changed=False, gathered=before)

        validate_hostname_platform(raw)
        changed = before != desired
        result = {"changed": changed, "before": before, "after": before,
                  "commands": [command] if changed else []}
        if changed:
            if module.check_mode:
                result["after"] = desired
            else:
                phase = "apply"
                write_attempted = True
                run_commands(module, [command])
                phase = "verification"
                raw, after = read_hostname(module)
                validate_hostname_platform(raw)
                if after != desired:
                    raise VerificationError("Hostname readback did not match the desired state")
                result["after"] = after
        if module._diff:
            result["diff"] = {"before": before, "after": result["after"]}
        module.exit_json(**result)
    except DrayTekError as exc:
        message = (
            f"Hostname {phase} failed ({type(exc).__name__}); device output suppressed"
            if isinstance(exc, (CommandError, DrayOSConnectionError))
            else str(exc)
        )
        if write_attempted:
            message += "; device may have changed, final state is not verified"
        module.fail_json(msg=message, changed=write_attempted)


if __name__ == "__main__":
    main()
