# Copyright: (c) 2026, kpeacocke
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: drayos_ntp
short_description: Manage the primary NTP server on a qualified DrayOS router
description:
  - Gather both NTP server fields or merge a primary server using C(sys time).
  - Configuration is restricted to Vigor2927Lac firmware 4.5.2.2.
  - The secondary server is preserved and verified, never configured.
  - Does not change time zones, clock values, synchronisation mode or enablement.
version_added: "0.1.0"
author:
  - kpeacocke (@kpeacocke)
options:
  state:
    description:
      - V(gathered) reads both server fields without changes.
      - V(parsed) parses O(running_config) without device access.
      - V(merged) changes only the primary server if its normalised value differs.
    type: str
    choices: [gathered, parsed, merged]
    default: gathered
  config:
    description: Desired primary server. Required and accepted only with V(merged).
    type: dict
    suboptions:
      primary_server:
        description:
          - Nonempty ASCII DNS name, without whitespace, quotes or a trailing dot.
          - DNS label lengths are validated locally; device rejection still fails the task.
          - Names compare case-insensitively.
        type: str
        required: true
  running_config:
    description: Complete C(sys time show) output. Required and accepted only with V(parsed).
    type: str
notes:
  - Requires C(ansible.netcommon.network_cli), except in V(parsed) state.
  - Requires C(ansible_network_single_user_mode=false); command caching is unsupported.
  - A write is successful only after both server fields match the expected state.
  - A failure after a write attempt reports C(changed=true) and C(state_may_have_changed=true).
    Inspect the device independently before retrying; no automatic rollback is attempted.
  - Returned server names and diffs may reveal internal infrastructure. Use task-level C(no_log)
    when that information must not be logged.
attributes:
  check_mode:
    description: Read current state and predict changes without configuration commands.
    support: full
  diff_mode:
    description: Report normalised server fields before and after the planned or verified change.
    support: full
"""

EXAMPLES = r"""
- name: Gather both NTP servers
  kpeacocke.draytek.drayos_ntp:
    state: gathered

- name: Set only the primary NTP server on qualified firmware
  kpeacocke.draytek.drayos_ntp:
    state: merged
    config:
      primary_server: time.cloudflare.com

- name: Parse previously captured time output
  kpeacocke.draytek.drayos_ntp:
    state: parsed
    running_config: "{{ time_output }}"
"""

RETURN = r"""
gathered:
  description: Both current server fields in V(gathered) state.
  returned: when state is gathered
  type: dict
parsed:
  description: Both server fields extracted from O(running_config).
  returned: when state is parsed
  type: dict
before:
  description: Both server fields before a V(merged) operation.
  returned: on successful merged state
  type: dict
after:
  description: Verified server fields, or predicted fields in check mode.
  returned: on successful merged state
  type: dict
state_may_have_changed:
  description: A configuration command was attempted but the operation did not complete successfully.
  returned: on failure after a write attempt
  type: bool
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
)
from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.ntp import (
    normalise_server,
    parse_ntp,
    require_ntp_write_platform,
)


def _read(module: AnsibleModule, command: str) -> str:
    responses = run_commands(module, [command])
    if not isinstance(responses, list) or len(responses) != 1 or not isinstance(responses[0], str):
        raise ParseError("Expected exactly one text response to the NTP read command")
    return responses[0]


def main() -> None:
    module = AnsibleModule(
        argument_spec={
            "state": {"type": "str", "choices": ["gathered", "parsed", "merged"], "default": "gathered"},
            "config": {"type": "dict", "options": {"primary_server": {"type": "str", "required": True}}},
            "running_config": {"type": "str", "no_log": True},
        },
        required_if=[("state", "parsed", ["running_config"]), ("state", "merged", ["config"])],
        supports_check_mode=True,
    )
    state = module.params["state"]
    for field, required_state in (("config", "merged"), ("running_config", "parsed")):
        if module.params[field] is not None and state != required_state:
            module.fail_json(msg=f"{field} is accepted only with state={required_state}", changed=False)

    write_attempted = False
    try:
        if state == "parsed":
            module.exit_json(changed=False, parsed=parse_ntp(module.params["running_config"]))
        if state == "gathered":
            module.exit_json(changed=False, gathered=parse_ntp(_read(module, "sys time show")))

        desired = normalise_server(module.params["config"]["primary_server"])
        require_ntp_write_platform(_read(module, "sys version"))
        before = parse_ntp(_read(module, "sys time show"))
        after = {**before, "primary_server": desired}
        changed = before != after
        if changed and not module.check_mode:
            write_attempted = True
            run_commands(module, [f"sys time server 1 {desired}"])
            observed = parse_ntp(_read(module, "sys time show"))
            if observed != after:
                module.fail_json(
                    msg="NTP readback did not match the requested primary and unchanged secondary; "
                        "inspect and recover the device independently before retrying",
                    changed=True, state_may_have_changed=True,
                )
            after = observed
        result = {"changed": changed, "before": before, "after": after}
        if module._diff:
            result["diff"] = {"before": before, "after": after}
        module.exit_json(**result)
    except DrayTekError as exc:
        message = (
            f"NTP operation failed ({type(exc).__name__}); device output suppressed"
            if isinstance(exc, (CommandError, DrayOSConnectionError))
            else str(exc)
        )
        module.fail_json(
            msg=message + ("; inspect and recover the device independently before retrying" if write_attempted else ""),
            changed=write_attempted,
            state_may_have_changed=write_attempted,
        )


if __name__ == "__main__":
    main()
