# Copyright: (c) 2026, kpeacocke
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations
DOCUMENTATION = r"""
---
module: drayos_facts
short_description: Collect facts from DrayOS devices
description:
  - Collect structured facts from a DrayOS device under
    C(ansible_facts.drayos). This module never mutates device state.
  - Parsing is validated against a sanitised Vigor2927Lac 4.5.2.2 live-device
    fixture. Other model and firmware combinations require their own
    validation; see C(docs/supported_devices.md).
version_added: "0.1.0"
author:
  - kpeacocke (@kpeacocke)
options:
  gather_subset:
    description:
      - Subsets of facts to collect. V(all) expands to every other choice.
    type: list
    elements: str
    default: [default]
    choices: [all, default, hardware, system, interfaces, wan, lan]
notes:
  - This module never reports C(changed=true).
"""

EXAMPLES = r"""
- name: Gather default facts
  kpeacocke.draytek.drayos_facts:

- name: Gather interface and WAN facts only
  kpeacocke.draytek.drayos_facts:
    gather_subset:
      - interfaces
      - wan
"""

RETURN = r"""
ansible_facts:
  description: Facts collected under the drayos key.
  returned: always
  type: dict
"""


from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.errors import (
    DrayTekError,
)
from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.connection import (
    run_commands,
)
from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos import (
    facts as facts_parsers,
)
from ansible.module_utils.basic import AnsibleModule


_ALL_SUBSETS = ("default", "hardware", "system", "interfaces", "wan", "lan")

_COMMAND_FOR_SUBSETS = {
    "sys version": {"default", "hardware", "system"},
    "sys iface": {"interfaces"},
    "show status": {"wan", "lan", "system"},
}


def resolve_subsets(requested: list) -> set:
    if "all" in requested:
        return set(_ALL_SUBSETS)
    return set(requested)


def commands_for_subsets(subsets: set) -> list:
    return [
        command
        for command, needed_by in _COMMAND_FOR_SUBSETS.items()
        if needed_by & subsets
    ]


def build_facts(subsets: set, responses: dict) -> dict:
    facts: dict = {}
    version_info = (
        facts_parsers.parse_sys_version(responses["sys version"])
        if "sys version" in responses
        else None
    )
    status_info = (
        facts_parsers.parse_show_status(responses["show status"])
        if "show status" in responses
        else None
    )

    if "default" in subsets and version_info is not None:
        facts["default"] = version_info.as_dict()
    if "hardware" in subsets and version_info is not None:
        facts["hardware"] = {
            "model": version_info.model,
            "hardware_version": version_info.hardware_version,
            "serial_number": version_info.serial_number,
        }
    if "system" in subsets:
        facts["system"] = {
            "firmware_version": version_info.firmware_version if version_info else None,
            "hostname": version_info.hostname if version_info else None,
            "uptime": status_info.get("uptime") if status_info else None,
        }
    if "interfaces" in subsets and "sys iface" in responses:
        facts["interfaces"] = facts_parsers.parse_sys_iface(
            responses["sys iface"])
    if "wan" in subsets and status_info is not None:
        facts["wan"] = status_info.get("wan", [])
    if "lan" in subsets and status_info is not None:
        facts["lan"] = {
            "ip_address": status_info.get("lan_ip_address"),
            "primary_dns": status_info.get("primary_dns"),
            "secondary_dns": status_info.get("secondary_dns"),
        }
    return facts


def main() -> None:
    argument_spec = dict(
        gather_subset=dict(
            type="list",
            elements="str",
            default=["default"],
            choices=["all", *_ALL_SUBSETS],
        ),
    )
    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=True)
    subsets = resolve_subsets(module.params["gather_subset"])
    commands = commands_for_subsets(subsets)

    try:
        results = run_commands(module, commands) if commands else []
    except DrayTekError as exc:
        module.fail_json(msg=str(exc))
        return

    module.exit_json(
        changed=False,
        ansible_facts={"drayos": build_facts(
            subsets, dict(zip(commands, results)))},
    )


if __name__ == "__main__":
    main()
