from __future__ import annotations

DOCUMENTATION = r"""
---
module: drayos_command
short_description: Run operational commands on DrayOS devices
description:
  - Send one or more operational (non-mutating) commands to a DrayOS device
    and return the output. This module never reports C(changed=true); it is
    an operational and diagnostic escape hatch, not a configuration module.
version_added: "0.1.0"
author:
  - kpeacocke
options:
  commands:
    description:
      - List of commands to send to the device. Each item may be a plain
        string, or a dictionary supporting O(wait_for), O(match), and
        O(command).
    type: list
    elements: raw
    required: true
  wait_for:
    description:
      - List of conditions to wait for before returning control to the task.
    type: list
    elements: str
  match:
    description:
      - Whether V(all) or V(any) of the O(wait_for) conditions must be met.
    type: str
    choices: [any, all]
    default: all
  retries:
    description:
      - Number of retries to perform before giving up on O(wait_for).
    type: int
    default: 10
  interval:
    description:
      - Interval, in seconds, between retries.
    type: int
    default: 1
notes:
  - This module never reports C(changed=true).
  - In check mode, only commands starting with C(show) are permitted, since
    this module does not distinguish mutating from non-mutating commands
    otherwise.
"""

EXAMPLES = r"""
- name: Run a single operational command
  kpeacocke.draytek.drayos_command:
    commands:
      - show system

- name: Run commands and wait for a condition
  kpeacocke.draytek.drayos_command:
    commands:
      - show interface
    wait_for:
      - result[0] contains "wan1"
"""

RETURN = r"""
stdout:
  description: The set of responses from the commands.
  returned: always
  type: list
  sample: ["..."]
stdout_lines:
  description: The value of stdout split into a list.
  returned: always
  type: list
  sample: [["..."]]
"""

import time

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.netcommon.plugins.module_utils.network.common.parsing import (
    Conditional,
)
from ansible_collections.ansible.netcommon.plugins.module_utils.network.common.utils import (
    to_lines,
    transform_commands,
)
from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.connection import (
    run_commands,
)
from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.errors import (
    ValidationError,
)


def parse_commands(module: AnsibleModule) -> list:
    commands = transform_commands(module)

    if module.check_mode:
        for command in commands:
            if not command["command"].startswith("show"):
                raise ValidationError(
                    "only show commands are supported when using check mode, "
                    f"received {command['command']!r}"
                )

    return commands


def main() -> None:
    argument_spec = dict(
        commands=dict(type="list", elements="raw", required=True),
        wait_for=dict(type="list", elements="str"),
        match=dict(type="str", default="all", choices=["any", "all"]),
        retries=dict(type="int", default=10),
        interval=dict(type="int", default=1),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    try:
        commands = parse_commands(module)
    except ValidationError as exc:
        module.fail_json(msg=str(exc))
        return

    wait_for = module.params["wait_for"] or []

    try:
        conditionals = [Conditional(condition) for condition in wait_for]
    except ValueError as exc:
        module.fail_json(msg=str(exc))
        return

    retries = module.params["retries"]
    interval = module.params["interval"]
    match = module.params["match"]

    result: dict = {"changed": False}
    responses: list = []
    for _ in range(retries):
        responses = run_commands(module, commands)

        for item in list(conditionals):
            if item(responses):
                if match == "any":
                    conditionals = []
                    break
                conditionals.remove(item)

        if not conditionals:
            break

        time.sleep(interval)

    if conditionals:
        failed_conditions = [item.raw for item in conditionals]
        msg = "One or more conditional statements have not been satisfied"
        module.fail_json(msg=msg, failed_conditions=failed_conditions)

    result.update(
        {
            "stdout": responses,
            "stdout_lines": list(to_lines(responses)),
        }
    )

    module.exit_json(**result)


if __name__ == "__main__":
    main()
