# Copyright: (c) 2026, kpeacocke
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: drayos_tr069
short_description: Read or approval-gated write DrayOS TR-069 parameters
description:
  - Read one leaf value or discover parameter names at the next subtree level.
  - Merged writes require exact platform, explicit confirmation, and mandatory readback.
  - The response formats are scoped to Vigor2927Lac firmware 4.5.2.2.
  - Configuration, recursive value retrieval and multi-line values are not supported.
version_added: "0.1.0"
author:
  - kpeacocke (@kpeacocke)
options:
  state:
    description:
      - V(gathered) queries the router.
      - V(parsed) parses O(running_config) without a connection.
      - V(merged) compares and writes one writable parameter with mandatory readback.
    type: str
    choices: [gathered, parsed, merged]
    default: gathered
  parameter:
    description:
      - Complete ASCII C(InternetGatewayDevice) parameter path.
      - O(query=names) requires a trailing dot; O(query=value) requires a leaf.
    type: str
    required: true
  query:
    description: Read a single value or next-level parameter names.
    type: str
    choices: [value, names]
    default: value
  running_config:
    description: Complete response to the selected query; required only with V(parsed).
    type: str
  value:
    description:
      - Desired value for V(state=merged).
    type: str
  confirmation:
    description:
      - Exact acknowledgement required before a write.
      - Must be C(I_AUTHORISE_TR069_WRITE).
    type: str
notes:
  - Requires C(ansible.netcommon.network_cli), except in V(parsed) state.
  - Requires task-level C(no_log=true), rejecting unprotected invocations before a read,
    because arbitrary parameters can contain credentials. Registered results remain
    usable; protect any subsequent tasks that consume them.
  - Requires C(ansible_persistent_log_messages=false). The cliconf plugin rejects
    these reads before sending a command if raw persistent logging is enabled.
  - Values are strings as received, without type conversion or whitespace trimming.
    Flag is opaque metadata, not an interpreted data type.
  - Writable reports the device metadata only and does not qualify a setter.
  - Missing or malformed framing fails rather than guessing an empty value.
  - An optional content-length header in names responses is recognised but its byte-count
    semantics have not been qualified; completeness uses declared count and unique paths.
attributes:
  check_mode:
    description: Perform the same read or offline parse without configuration writes.
    support: full
  diff_mode:
    description: Merged writes support redacted before/after diffs.
    support: full
"""

EXAMPLES = r"""
- name: Read product information privately
  kpeacocke.draytek.drayos_tr069:
    parameter: InternetGatewayDevice.DeviceInfo.Manufacturer
  register: manufacturer
  no_log: true

- name: Discover next-level parameter names
  kpeacocke.draytek.drayos_tr069:
    query: names
    parameter: InternetGatewayDevice.DeviceInfo.
  register: device_parameters
  no_log: true
"""

RETURN = r"""
gathered:
  description:
    - For value queries, contains parameter, value, opaque flag and writable metadata.
    - For names queries, contains parameter, count and the list of names.
    - Requires task-level no_log; may contain credentials.
  returned: when state is gathered
  type: dict
parsed:
  description: The same structure as RV(gathered), parsed offline.
  returned: when state is parsed
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.connection import (
    MAX_PAGE_ADVANCES,
    PAGER_PROMPT,
    run_commands,
)
from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.errors import (
    DrayTekError,
    ParseError,
)
from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.tr069 import (
    parse_names,
    parse_value,
    read_command,
    validate_write_value,
    write_command,
)
from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.facts import (
    parse_sys_version,
)


def main() -> None:
    module = AnsibleModule(
        argument_spec={
            "state": {"type": "str", "choices": ["gathered", "parsed", "merged"], "default": "gathered"},
            "parameter": {"type": "str", "required": True},
            "query": {"type": "str", "choices": ["value", "names"], "default": "value"},
            "running_config": {"type": "str", "no_log": True},
            "value": {"type": "str"},
            "confirmation": {"type": "str"},
        },
        required_if=[
            ("state", "parsed", ["running_config"]),
            ("state", "merged", ["value", "confirmation"]),
        ],
        supports_check_mode=True,
    )
    if not module.no_log:
        module.fail_json(msg="TR-069 requires task-level no_log: true before reading parameter data",
                         changed=False)
    state = module.params["state"]
    parameter = module.params["parameter"]
    query = module.params["query"]
    if state != "parsed" and module.params["running_config"] is not None:
        module.fail_json(msg="running_config is accepted only with state=parsed", changed=False)
    if state == "merged" and query != "value":
        module.fail_json(msg="TR-069 writes require query=value", changed=False)
    if state == "merged" and module.params["confirmation"] != "I_AUTHORISE_TR069_WRITE":
        module.fail_json(msg="TR-069 write requires exact confirmation", changed=False)
    try:
        if state == "merged":
            validate_write_value(module.params["value"])
        if state == "merged":
            platform_responses = run_commands(module, [{"command": "sys version"}])
            if not isinstance(platform_responses, list) or len(platform_responses) != 1 or not isinstance(platform_responses[0], str):
                raise ParseError("Expected exactly one sys version response")
            platform = parse_sys_version(platform_responses[0])
            if platform.model != "Vigor2927Lac" or platform.firmware_version != "4.5.2.2":
                module.fail_json(msg="TR-069 writes are supported only on Vigor2927Lac firmware 4.5.2.2", changed=False)
        command = read_command(parameter, query)
        if state == "parsed":
            output = module.params["running_config"]
        else:
            request: dict[str, object] = {"command": command}
            if query == "names":
                request.update(prompt=[PAGER_PROMPT] * MAX_PAGE_ADVANCES,
                               answer=[" "] * MAX_PAGE_ADVANCES, newline=False, check_all=True)
            responses = run_commands(module, [request])
            if not isinstance(responses, list) or len(responses) != 1 or not isinstance(responses[0], str):
                raise ParseError("Expected exactly one text response to the TR-069 query")
            output = responses[0]
        result = parse_names(output, parameter) if query == "names" else parse_value(output, parameter)
        if state != "merged":
            module.exit_json(changed=False, **{state: result})
            return

        if result["writable"] is not True:
            module.fail_json(msg="TR-069 parameter is not writable", changed=False)

        desired = module.params["value"]
        command = write_command(parameter, desired)
        if result["value"] == desired:
            module.exit_json(changed=False, **{"merged": result})
            return
        if module.check_mode:
            predicted = dict(result)
            predicted["value"] = desired
            diff = {"before": {"value": "<redacted>"}, "after": {"value": "<redacted>"}}
            module.exit_json(changed=True, diff=diff, **{"merged": predicted})
            return

        set_responses = run_commands(module, [{"command": command}])
        if not isinstance(set_responses, list) or len(set_responses) != 1 or not isinstance(set_responses[0], str):
            raise ParseError("Expected exactly one TR-069 write response")
        verify_responses = run_commands(module, [{"command": read_command(parameter, "value")}])
        if not isinstance(verify_responses, list) or len(verify_responses) != 1 or not isinstance(verify_responses[0], str):
            raise ParseError("Expected exactly one TR-069 readback response")
        verified = parse_value(verify_responses[0], parameter)
        if verified["value"] != desired:
            module.fail_json(
                msg="TR-069 write was sent but readback did not match; state may have changed",
                changed=True,
                state_may_have_changed=True,
            )
            return
        diff = {"before": {"value": "<redacted>"}, "after": {"value": "<redacted>"}}
        module.exit_json(changed=True, diff=diff, **{"merged": verified})
    except DrayTekError as exc:
        module.fail_json(msg=f"TR-069 read failed ({type(exc).__name__}); device output suppressed",
                         changed=False)


if __name__ == "__main__":
    main()
