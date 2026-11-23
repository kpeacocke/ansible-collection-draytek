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
  state:
    description:
      - C(gathered) connects through network_cli and reads the device.
      - C(parsed) parses O(running_config) locally and never opens a device connection.
    type: str
    choices: [gathered, parsed]
    default: gathered
  running_config:
    description:
      - Synthetic C(sys version) output used only by O(state=parsed).
    type: str
  gather_subset:
    description:
      - Subsets of facts to collect. V(all) expands to every other choice.
    type: list
    elements: str
    default: [default]
    choices: [all, default, hardware, system, interfaces, wan, lan]
  gather_lan_profiles:
    description:
      - Also collect configured IPv4 settings for LAN1 to LAN8 using C(show lan).
      - Independent of O(gather_subset); existing subset output is unchanged.
      - Verified response framing targets Vigor2927Lac firmware 4.5.2.2.
    type: bool
    default: false
  gather_ipv4_routes:
    description:
      - Also collect the IPv4 route status table using C(ip route status).
      - Independent of O(gather_subset); existing subset output is unchanged.
    type: bool
    default: false
  gather_vlan_slots:
    description:
      - Also collect configured VLAN slots using C(vlan status).
      - Independent of O(gather_subset); existing subset output is unchanged.
    type: bool
    default: false
  gather_vlan_p1_untagged_access:
    description:
      - Also collect whether the router is configured to permit access from untagged devices on P1 using C(vlan status).
      - Independent of O(gather_subset); existing subset output is unchanged.
    type: bool
    default: false
  gather_nat_redirects:
    description:
      - Also collect the documented NAT port-redirection status table using C(srv nat status).
      - Independent of O(gather_subset); existing subset output is unchanged.
      - Qualified on Vigor2927Lac firmware 4.5.2.2. The table includes placeholder rows and private IPv4 addresses.
        Use task-level C(no_log), disable persistent command logging and consider whether fact caching is appropriate.
    type: bool
    default: false
  gather_dhcp_leases:
    description:
      - Also collect the IPv4 DHCP lease table using C(srv dhcp status).
      - Independent of O(gather_subset); existing subset output is unchanged.
      - Results contain client identifiers. Use task-level C(no_log) if they must not appear in task output,
        and do not cache them if the fact cache is not suitable for this data.
    type: bool
    default: false
  gather_dhcp_lease_time:
    description:
      - Also collect the lease duration in seconds reported by C(srv dhcp leasetime ?).
      - Independent of O(gather_subset); existing subset output is unchanged.
      - The command reports a single value without identifying a LAN. It is not an active lease timer.
    type: bool
    default: false
  gather_dhcp2_status:
    description:
      - Also collect the secondary DHCP server mode and port flags using C(srv dhcp dhcp2 -v).
      - Independent of O(gather_subset); existing subset output is unchanged.
      - These are reported flags, not proof that the server is serving clients.
    type: bool
    default: false
  gather_wan_links:
    description:
      - Also collect the online and stall indicators from numbered WAN and PVC WAN headers using C(wan status).
      - Independent of O(gather_subset); existing subset output is unchanged.
    type: bool
    default: false
  gather_lte_access:
    description:
      - Also collect LTE access technology using C(wan lte stus).
      - Independent of O(gather_subset); existing subset output is unchanged.
      - Requires persistent transport logging to be disabled because the raw response contains modem identifiers.
    type: bool
    default: false
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
  description:
    - Facts collected under the drayos key.
    - When O(gather_lan_profiles=true), C(lan_profiles) maps each numbered LAN to
      enabled, ip_address, netmask, dhcp_enabled, dhcp_start_ip, dhcp_pool_size
      and dhcp_gateway. Values describe configuration, not active leases.
    - When O(gather_ipv4_routes=true), C(ipv4_routes) lists destination (CIDR),
      flags (as reported), next_hop (null when directly connected), and interface.
    - When O(gather_vlan_slots=true), C(vlan_slots) lists slot, enabled, vid,
      priority, lan and members. These are configured row values, not effective
      forwarding state or the global VLAN enable flag.
    - When O(gather_vlan_p1_untagged_access=true), C(vlan_p1_untagged_access) is a
      boolean configuration value, not a reachability check or the global VLAN enable flag.
    - When O(gather_nat_redirects=true), C(nat_redirects) lists the reported index,
      protocol number, public port, private IPv4 address and private port for each row.
      Placeholder rows are retained; the module does not infer that a row is active.
    - When O(gather_dhcp_leases=true), C(dhcp_leases) lists lan, index, ip_address,
      mac_address, lease_time (display text) and host_id (null when absent).
      Embedded horizontal tabs in host_id are preserved.
      This is a point-in-time lease table, not a reservation or pool configuration export.
    - When O(gather_dhcp_lease_time=true), C(dhcp_lease_time_seconds) is the
      single duration reported by the command, not a per-LAN or per-client lease timer.
    - When O(gather_dhcp2_status=true), C(dhcp2_status) contains boolean
      C(mac_address_mode), C(lan_port_mode), C(port_1) and C(port_2) flags.
    - When O(gather_wan_links=true), C(wan_links) lists interface, online and stalled
      for the numbered WAN and PVC WAN headers. This excludes traffic, addressing and other status blocks.
    - When O(gather_lte_access=true), C(lte_access) contains C(access_technology),
      which is V(LTE) or null when the device leaves it unspecified or displays a placeholder.
      It is not a connectivity check.
  returned: always
  type: dict
"""


from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.errors import (
    DrayTekError,
    ParseError,
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
        state=dict(type="str", choices=["gathered", "parsed"], default="gathered"),
        running_config=dict(type="str"),
        gather_subset=dict(
            type="list",
            elements="str",
            default=["default"],
            choices=["all", *_ALL_SUBSETS],
        ),
        gather_lan_profiles=dict(type="bool", default=False),
        gather_ipv4_routes=dict(type="bool", default=False),
        gather_vlan_slots=dict(type="bool", default=False),
        gather_vlan_p1_untagged_access=dict(type="bool", default=False),
        gather_nat_redirects=dict(type="bool", default=False),
        gather_dhcp_leases=dict(type="bool", default=False),
        gather_dhcp_lease_time=dict(type="bool", default=False),
        gather_dhcp2_status=dict(type="bool", default=False),
        gather_wan_links=dict(type="bool", default=False),
        gather_lte_access=dict(type="bool", default=False),
    )
    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=True)
    if module.params["state"] == "parsed":
        running_config = module.params["running_config"]
        if not running_config:
            module.fail_json(msg="running_config is required for state=parsed")
            return
        subsets = resolve_subsets(module.params["gather_subset"])
        facts = build_facts(subsets, {"sys version": running_config})
        module.exit_json(changed=False, ansible_facts={"drayos": facts})
        return
    subsets = resolve_subsets(module.params["gather_subset"])
    commands = commands_for_subsets(subsets)
    optional_facts = [
        (command, key, parser)
        for option, command, key, parser in (
            ("gather_lan_profiles", "show lan", "lan_profiles", facts_parsers.parse_lan_profiles),
            ("gather_ipv4_routes", "ip route status", "ipv4_routes", facts_parsers.parse_ipv4_routes),
            ("gather_vlan_slots", "vlan status", "vlan_slots", facts_parsers.parse_vlan_slots),
            ("gather_vlan_p1_untagged_access", "vlan status", "vlan_p1_untagged_access", facts_parsers.parse_vlan_p1_untagged_access),
            ("gather_nat_redirects", "srv nat status", "nat_redirects", facts_parsers.parse_nat_redirects),
            ("gather_dhcp_leases", "srv dhcp status", "dhcp_leases", facts_parsers.parse_dhcp_leases),
            ("gather_dhcp_lease_time", "srv dhcp leasetime ?", "dhcp_lease_time_seconds", facts_parsers.parse_dhcp_lease_time),
            ("gather_dhcp2_status", "srv dhcp dhcp2 -v", "dhcp2_status", facts_parsers.parse_dhcp2_status),
            ("gather_wan_links", "wan status", "wan_links", facts_parsers.parse_wan_links),
            ("gather_lte_access", "wan lte stus", "lte_access", facts_parsers.parse_lte_access),
        )
        if module.params[option]
    ]
    commands.extend(dict.fromkeys(entry[0] for entry in optional_facts))

    try:
        results = run_commands(module, commands) if commands else []
        if optional_facts and (
            not isinstance(results, list) or len(results) != len(commands)
            or not all(isinstance(result, str) for result in results)
        ):
            raise ParseError("Expected one text response per facts command")
        responses = dict(zip(commands, results))
        facts = build_facts(subsets, responses)
        for command, key, parser in optional_facts:
            facts[key] = parser(responses[command])
    except DrayTekError as exc:
        message = str(exc)
        if optional_facts and not isinstance(exc, ParseError):
            message = "Extended facts gathering failed; device output suppressed"
        module.fail_json(msg=message, changed=False)
        return

    module.exit_json(changed=False, ansible_facts={"drayos": facts})


if __name__ == "__main__":
    main()
