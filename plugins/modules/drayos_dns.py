# Copyright: (c) 2026, kpeacocke
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: drayos_dns
short_description: Read the IPv4 DNS settings reported for DrayOS LANs
description:
  - Gather the primary and secondary IPv4 DNS fields for LAN1 through LAN8.
  - Does not change configuration or report effective upstream resolver selection.
version_added: "0.1.0"
author:
  - kpeacocke (@kpeacocke)
options:
  state:
    description:
      - V(gathered) reads the device.
      - V(parsed) parses an existing response without a connection.
    choices: [gathered, parsed]
    type: str
    default: gathered
  running_config:
    description: Complete response to C(show dns), accepted only with V(parsed).
    type: str
notes:
  - Disable persistent connection logging and use task-level C(no_log=true) if
    resolver addresses are private.
  - The response format targets Vigor2927Lac firmware 4.5.2.2.
attributes:
  check_mode:
    description: Performs the same read or offline parse without changing configuration.
    support: full
  diff_mode:
    description: There are no configuration changes.
    support: none
"""

EXAMPLES = r"""
- name: Read LAN DNS settings privately
  kpeacocke.draytek.drayos_dns:
  register: lan_dns
  no_log: true
"""

RETURN = r"""
gathered:
  description:
    - Mapping of LAN1 through LAN8 to primary and secondary fields.
    - Each field is an IPv4 string or null when the device reports it as not set.
  returned: when state is gathered
  type: dict
parsed:
  description: The same mapping as RV(gathered), parsed without a connection.
  returned: when state is parsed
  type: dict
"""

from ipaddress import AddressValueError, IPv4Address
import re

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.connection import (
    MAX_PAGE_ADVANCES,
    PAGER_PROMPT,
    run_commands,
)
from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.errors import DrayTekError, ParseError


_HEADER = re.compile(r"[ \t%]*Domain name server settings:[ \t]*")
_ROW = re.compile(r"[ \t%]*(LAN[1-8])[ \t]+(Primary|Secondary)[ \t]+DNS[ \t]*:[ \t]*(.*?)[ \t]*")
_LAN_ROW = re.compile(r"[ \t%]*LAN[1-8]\b")


def parse_lan_dns(output: str) -> dict[str, dict[str, str | None]]:
    entries: dict[str, dict[str, str | None]] = {f"LAN{i}": {} for i in range(1, 9)}
    header = False
    for line in output.splitlines():
        if _HEADER.fullmatch(line):
            if header:
                raise ParseError("Duplicate DNS response header")
            header = True
        elif _LAN_ROW.match(line):
            row = _ROW.fullmatch(line)
            if not header or row is None:
                raise ParseError("Unrecognised LAN DNS row")
            lan, label, value = row.groups()
            field = label.lower()
            if field in entries[lan]:
                raise ParseError("Duplicate LAN DNS row")
            if value == "[Not set]":
                entries[lan][field] = None
            else:
                try:
                    entries[lan][field] = str(IPv4Address(value))
                except AddressValueError as exc:
                    raise ParseError("Invalid address in LAN DNS row") from exc
    if not header or any(set(fields) != {"primary", "secondary"} for fields in entries.values()):
        raise ParseError("Incomplete LAN DNS response")
    return entries


def main() -> None:
    module = AnsibleModule(
        argument_spec={
            "state": {"type": "str", "choices": ["gathered", "parsed"], "default": "gathered"},
            "running_config": {"type": "str", "no_log": True},
        },
        required_if=[("state", "parsed", ["running_config"])],
        supports_check_mode=True,
    )
    state = module.params["state"]
    output = module.params["running_config"]
    if state == "gathered" and output is not None:
        module.fail_json(msg="running_config is accepted only with state=parsed", changed=False)

    try:
        if state == "gathered":
            response = run_commands(module, [{
                "command": "show dns",
                "prompt": [PAGER_PROMPT] * MAX_PAGE_ADVANCES,
                "answer": [" "] * MAX_PAGE_ADVANCES,
                "newline": False,
                "check_all": True,
            }])
            if not isinstance(response, list) or len(response) != 1 or not isinstance(response[0], str):
                raise ParseError("Expected one text response to show dns")
            output = response[0]
        module.exit_json(changed=False, **{state: parse_lan_dns(output)})
    except DrayTekError as exc:
        module.fail_json(msg=f"LAN DNS read failed ({type(exc).__name__}); device output suppressed", changed=False)


if __name__ == "__main__":
    main()
