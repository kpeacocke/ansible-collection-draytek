# Copyright: (c) 2026, kpeacocke
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import annotations

DOCUMENTATION = r"""
---
module: drayos_dns
short_description: Read DrayOS LAN DNS settings and manage resolvers on disabled LAN7
description:
  - Gather the primary and secondary IPv4 DNS fields for LAN1 through LAN8.
  - Set or clear one IPv4 DNS field at a time on a disabled LAN7 only.
  - Does not report effective upstream resolver selection.
version_added: "0.1.0"
author:
  - kpeacocke (@kpeacocke)
options:
  state:
    description:
      - V(gathered) reads the device.
      - V(parsed) parses an existing response without a connection.
      - V(merged) manages one DNS field on disabled LAN7.
    choices: [gathered, parsed, merged]
    type: str
    default: gathered
  running_config:
    description: Complete response to C(show dns), accepted only with V(parsed).
    type: str
  lan:
    description: Target LAN, required only with V(merged).
    choices: [LAN7]
    type: str
  primary_server:
    description:
      - Desired primary IPv4 address, accepted only with V(merged).
      - Use V(0.0.0.0) to clear the field.
      - Mutually exclusive with O(secondary_server).
    type: str
  secondary_server:
    description:
      - Desired secondary IPv4 address, accepted only with V(merged).
      - Use V(0.0.0.0) to clear the field.
      - Mutually exclusive with O(primary_server).
    type: str
notes:
  - Disable persistent connection logging and use task-level C(no_log=true) if
    resolver addresses are private.
  - The response format targets Vigor2927Lac firmware 4.5.2.2.
  - Writes are restricted to that exact model and firmware and require LAN7 to be disabled.
  - V(merged) requires either O(primary_server) or O(secondary_server), not both.
  - Readback verifies all eight LAN DNS pairs; other fields are not managed.
attributes:
  check_mode:
    description: Performs reads and predicts changes without writing.
    support: full
  diff_mode:
    description: Return the current and desired server in merged state.
    support: full
"""

EXAMPLES = r"""
- name: Read LAN DNS settings privately
  kpeacocke.draytek.drayos_dns:
  register: lan_dns
  no_log: true

- name: Clear primary DNS on a disabled LAN7
  kpeacocke.draytek.drayos_dns:
    state: merged
    lan: LAN7
    primary_server: "0.0.0.0"
  no_log: true

- name: Set secondary DNS on a disabled LAN7
  kpeacocke.draytek.drayos_dns:
    state: merged
    lan: LAN7
    secondary_server: "192.0.2.54"
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
before:
  description: Selected server before the change, or null if unset.
  returned: on success when state is merged
  type: str
after:
  description: Verified or predicted selected server, or null if unset.
  returned: on success when state is merged
  type: str
state_may_have_changed:
  description: Whether a failed invocation attempted a write.
  returned: on operation failure
  type: bool
"""

from ipaddress import AddressValueError, IPv4Address
import re

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.connection import (
    MAX_PAGE_ADVANCES,
    PAGER_PROMPT,
    run_commands,
)
from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.errors import (
    DrayTekError,
    ParseError,
    UnsupportedPlatformError,
    ValidationError,
)
from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.facts import parse_sys_version


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


def _read(module: AnsibleModule, command: str, *, paged: bool = False) -> str:
    request: dict[str, object] = {"command": command}
    if paged:
        request.update(prompt=[PAGER_PROMPT] * MAX_PAGE_ADVANCES,
                       answer=[" "] * MAX_PAGE_ADVANCES, newline=False, check_all=True)
    response = run_commands(module, [request])
    if not isinstance(response, list) or len(response) != 1 or not isinstance(response[0], str):
        raise ParseError("Expected one DNS operation response")
    return response[0]


def _require_write_target(module: AnsibleModule) -> None:
    version = _read(module, "sys version")
    platform = parse_sys_version(version)
    if (platform.model, platform.firmware_version) != ("Vigor2927Lac", "4.5.2.2") or (
        len(re.findall(r"^[ \t]*Router Model:", version, re.MULTILINE)) != 1
        or len(re.findall(r"\bVersion:", version)) != 1
    ):
        raise UnsupportedPlatformError("DNS writes require Vigor2927Lac firmware 4.5.2.2")
    lan = _read(module, "show lan", paged=True)
    rows = re.findall(r"^[ \t%]*\[([^\]\r\n]+)\][ \t]*LAN7(?=[ \t])", lan, re.MULTILINE)
    if rows != ["X"]:
        raise ValidationError("DNS writes require an unambiguous disabled LAN7")


def main() -> None:
    module = AnsibleModule(
        argument_spec={
            "state": {"type": "str", "choices": ["gathered", "parsed", "merged"], "default": "gathered"},
            "running_config": {"type": "str", "no_log": True},
            "lan": {"type": "str", "choices": ["LAN7"]},
            "primary_server": {"type": "str"},
            "secondary_server": {"type": "str"},
        },
        required_if=[
            ("state", "parsed", ["running_config"]),
            ("state", "merged", ["lan"]),
            ("state", "merged", ["primary_server", "secondary_server"], True),
        ],
        mutually_exclusive=[("primary_server", "secondary_server")],
        supports_check_mode=True,
    )
    state = module.params["state"]
    for field, mode in (("running_config", "parsed"), ("lan", "merged"),
                        ("primary_server", "merged"), ("secondary_server", "merged")):
        if state != mode and module.params[field] is not None:
            module.fail_json(msg=f"{field} is accepted only with state={mode}", changed=False)

    write_attempted = False
    try:
        if state == "parsed":
            module.exit_json(changed=False, parsed=parse_lan_dns(module.params["running_config"]))
        if state == "gathered":
            module.exit_json(changed=False, gathered=parse_lan_dns(_read(module, "show dns", paged=True)))

        option = "primary_server" if module.params["primary_server"] is not None else "secondary_server"
        field = "primary" if option == "primary_server" else "secondary"
        try:
            address = IPv4Address(module.params[option])
        except AddressValueError as exc:
            raise ValidationError(f"{option} must be a dotted IPv4 address") from exc
        if address.is_multicast or address == IPv4Address("255.255.255.255"):
            raise ValidationError(f"{option} must not be multicast or broadcast")
        desired = None if address.is_unspecified else str(address)
        _require_write_target(module)
        before = parse_lan_dns(_read(module, "show dns", paged=True))
        current = before["LAN7"][field]
        changed = current != desired
        if changed and not module.check_mode:
            expected = {**before, "LAN7": {**before["LAN7"], field: desired}}
            write_attempted = True
            command = "dns1" if field == "primary" else "dns2"
            run_commands(module, [f"srv dhcp {command} lan7 {address}"])
            if parse_lan_dns(_read(module, "show dns", paged=True)) != expected:
                raise ParseError("DNS readback did not match the requested change and unchanged other LAN fields")
        result = {"changed": changed, "before": current, "after": desired}
        if module._diff:
            result["diff"] = {"before": {option: current}, "after": {option: desired}}
        module.exit_json(**result)
    except DrayTekError as exc:
        message = str(exc) if isinstance(exc, (ParseError, UnsupportedPlatformError, ValidationError)) else (
            f"LAN DNS operation failed ({type(exc).__name__}); device output suppressed"
        )
        if write_attempted:
            message += "; inspect the current DNS settings and recover independently before retrying"
        module.fail_json(msg=message, changed=write_attempted, state_may_have_changed=write_attempted)


if __name__ == "__main__":
    main()
