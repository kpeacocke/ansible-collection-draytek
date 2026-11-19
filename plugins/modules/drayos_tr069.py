# Copyright: (c) 2026, kpeacocke
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: drayos_tr069
short_description: Read DrayOS TR-069 parameters without configuration writes
description:
  - Read one leaf value or discover parameter names at the next subtree level.
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
    type: str
    choices: [gathered, parsed]
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
  - The content-length header in names responses is recognised but its byte-count
    semantics have not been qualified; completeness uses declared count and unique paths.
attributes:
  check_mode:
    description: Perform the same read or offline parse without configuration writes.
    support: full
  diff_mode:
    description: No configuration changes are made.
    support: none
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
)


def main() -> None:
    module = AnsibleModule(
        argument_spec={
            "state": {"type": "str", "choices": ["gathered", "parsed"], "default": "gathered"},
            "parameter": {"type": "str", "required": True},
            "query": {"type": "str", "choices": ["value", "names"], "default": "value"},
            "running_config": {"type": "str", "no_log": True},
        },
        required_if=[("state", "parsed", ["running_config"])],
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
    try:
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
        module.exit_json(changed=False, **{state: result})
    except DrayTekError as exc:
        module.fail_json(msg=f"TR-069 read failed ({type(exc).__name__}); device output suppressed",
                         changed=False)


if __name__ == "__main__":
    main()
