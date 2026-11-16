# Copyright: (c) 2026, kpeacocke
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: drayos_hostname
short_description: Read a DrayOS router hostname
description:
  - Gather a router hostname using C(sys version), or parse supplied output.
  - Hostname configuration is not supported.
  - The read format is validated against Vigor2927Lac firmware 4.5.2.2.
    Other models and firmware require separate validation.
version_added: "0.1.0"
author:
  - kpeacocke (@kpeacocke)
options:
  state:
    description:
      - V(gathered) reads the current hostname without writes.
      - V(parsed) parses O(running_config) without connecting to a device.
    type: str
    choices: [gathered, parsed]
    default: gathered
  running_config:
    description: Complete C(sys version) output. Required and accepted only with V(parsed).
    type: str
notes:
  - Requires C(ansible.netcommon.network_cli), except in V(parsed) state.
  - Requires C(ansible_network_single_user_mode=false), the default.
    DrayOS command caching is unsupported and is rejected before execution.
attributes:
  check_mode:
    description: Read or parse the hostname without configuration writes.
    support: full
  diff_mode:
    description: No configuration changes are made, so no diff is returned.
    support: none
"""

EXAMPLES = r"""
- name: Gather the router hostname
  kpeacocke.draytek.drayos_hostname:
    state: gathered

- name: Parse previously captured system output
  kpeacocke.draytek.drayos_hostname:
    state: parsed
    running_config: "{{ system_version_output }}"
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
from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.hostname import (
    parse_hostname,
)


def main() -> None:
    module = AnsibleModule(
        argument_spec={
            "state": {"type": "str", "choices": ["gathered", "parsed"],
                      "default": "gathered"},
            "running_config": {"type": "str", "no_log": True},
        },
        required_if=[("state", "parsed", ["running_config"])],
        supports_check_mode=True,
    )
    state = module.params["state"]
    if module.params["running_config"] is not None and state != "parsed":
        module.fail_json(msg="running_config is accepted only with state=parsed")

    try:
        if state == "parsed":
            module.exit_json(changed=False, parsed=parse_hostname(module.params["running_config"]))
        responses = run_commands(module, ["sys version"])
        if not isinstance(responses, list) or len(responses) != 1 or not isinstance(responses[0], str):
            raise ParseError("Expected exactly one text response to sys version")
        module.exit_json(changed=False, gathered=parse_hostname(responses[0]))
    except DrayTekError as exc:
        message = (
            f"Hostname gather failed ({type(exc).__name__}); device output suppressed"
            if isinstance(exc, (CommandError, DrayOSConnectionError))
            else str(exc)
        )
        module.fail_json(msg=message, changed=False)


if __name__ == "__main__":
    main()
