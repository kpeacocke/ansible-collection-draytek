# Copyright: (c) 2026, kpeacocke
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Parsers for DrayOS CLI output.

The parser is validated against a sanitised Vigor2927Lac 4.5.2.2 live-device
fixture. The older Vigor2927 4.4.0 fixture remains documentation evidence.
"""
from __future__ import annotations

import re
from ipaddress import AddressValueError, IPv4Address, IPv4Network

from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.connection import PAGER_PROMPT
from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.errors import ParseError

from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.models import (
    PlatformInfo,
)

_SYS_VERSION_PATTERNS = {
    "hostname": re.compile(r"^[ \t]*Router Name:[ \t]*([^\r\n]*)", re.MULTILINE),
    "model": re.compile(r"^[ \t]*Router Model:[ \t]*(\S+)", re.MULTILINE),
    "version": re.compile(
        r"^[ \t]*(?:Router Model:[ \t]*\S+[ \t]+)?Version:[ \t]*(\S+)", re.MULTILINE
    ),
    "revision": re.compile(r"Revision:\s*(.+)"),
    "serial_no": re.compile(r"Router serial no:\s*(.+)"),
}


def parse_sys_version(text: str) -> PlatformInfo:
    """Parse documented ``sys version`` output into platform facts."""
    values: dict[str, str] = {}
    for key, pattern in _SYS_VERSION_PATTERNS.items():
        match = pattern.search(text)
        if match:
            values[key] = match.group(1).strip()

    serial = values.get("serial_no")
    if serial in (None, "None", ""):
        serial = None

    return PlatformInfo(
        model=values.get("model"),
        hostname=values.get("hostname") or None,
        firmware_version=values.get("version"),
        hardware_version=values.get("revision"),
        serial_number=serial,
    )


_LAN_HEADER = re.compile(r"[ \t%]*The LAN settings:[ \t]*")
_LAN_PROFILE_PREFIX = re.compile(r"[ \t%]*(?:\[[^\r\n]*\][ \t]*)?LAN[1-8]\b")
_LAN_PROFILE_ROW = re.compile(
    r"[ \t%]*\[([VX])\][ \t]*(LAN[1-8])[ \t]+([0-9.]+)[ \t]+([0-9.]+)[ \t]+"
    r"([VX])[ \t]+([0-9.]+)[ \t]+([0-9]{1,10})[ \t]+([0-9.]+)[ \t]*"
)


def parse_lan_profiles(text: str) -> dict[str, dict[str, str | int | bool]]:
    """Parse the eight numbered profiles, excluding the separate routed profile."""
    header = False
    profiles: dict[str, dict[str, str | int | bool]] = {}
    for line in text.splitlines():
        if _LAN_HEADER.fullmatch(line):
            if header:
                raise ParseError("Duplicate LAN settings header")
            header = True
        elif _LAN_PROFILE_PREFIX.match(line):
            row = _LAN_PROFILE_ROW.fullmatch(line)
            if not header or row is None:
                raise ParseError("Unrecognised LAN profile row")
            enabled, name, address, mask, dhcp, start, count, gateway = row.groups()
            if name in profiles:
                raise ParseError("Duplicate LAN profile row")
            try:
                profiles[name] = {
                    "enabled": enabled == "V",
                    "ip_address": str(IPv4Address(address)),
                    "netmask": str(IPv4Address(mask)),
                    "dhcp_enabled": dhcp == "V",
                    "dhcp_start_ip": str(IPv4Address(start)),
                    "dhcp_pool_size": int(count),
                    "dhcp_gateway": str(IPv4Address(gateway)),
                }
            except AddressValueError as exc:
                raise ParseError("Invalid address in LAN profile row") from exc
    if len(profiles) != 8:
        raise ParseError("Incomplete LAN settings response")
    return profiles


_IPV4_ROUTE_LEGEND = re.compile(
    r"Codes:\s*C - connected,\s*S - static,\s*R - RIP,\s*\* - default,\s*~ - private"
    r"(?:,[ \t]*[A-Za-z*~?!=+-]{1,4}[ \t]+-[ \t]+[A-Za-z][A-Za-z0-9 /_-]{0,63})*"
)
_IPV4_ROUTE_ROW = re.compile(
    r"([CSR*~]+)[ \t]+([0-9.]+)/[ \t]*([0-9.]+)[ \t]+"
    r"(?:is directly connected|via[ \t]+([0-9.]+)),[ \t]*([A-Za-z0-9][A-Za-z0-9 _./-]*)"
)


def parse_ipv4_routes(text: str) -> list[dict[str, str | None]]:
    """Parse documented route rows without silently dropping unknown routes."""
    legend = False
    routes = []
    awaiting_page = False
    for raw in text.splitlines():
        line = raw.lstrip(" \t%").rstrip()
        if not line:
            continue
        if _IPV4_ROUTE_LEGEND.fullmatch(line) and not legend:
            legend = True
            continue
        if routes and not awaiting_page and re.fullmatch(PAGER_PROMPT, line):
            awaiting_page = True
            continue
        row = _IPV4_ROUTE_ROW.fullmatch(line)
        if not legend or row is None:
            raise ParseError("Unrecognised IPv4 route table line")
        flags, address, mask, gateway, interface = row.groups()
        try:
            network = IPv4Network(f"{address}/{mask}", strict=True)
            if str(network.netmask) != mask:
                raise ValueError("Expected a network mask")
            routes.append({
                "destination": str(network),
                "flags": flags,
                "next_hop": str(IPv4Address(gateway)) if gateway is not None else None,
                "interface": interface,
            })
            awaiting_page = False
        except ValueError as exc:
            raise ParseError("Invalid address or mask in IPv4 route table") from exc
    if awaiting_page:
        raise ParseError("Incomplete paginated IPv4 route table")
    if not routes:
        raise ParseError("Missing or empty IPv4 route table")
    return routes


_VLAN_HEADER = re.compile(
    r" *VLAN +Enable +VID +Pri +(?P<ports>p1 p2 p3 p4 p5 s1 s2 s3 s4 5gs1 5gs2 5gs3 5gs4) +(?P<subnet>subnet)",
    re.IGNORECASE,
)
_VLAN_ROW = re.compile(
    r" *(?P<slot>[0-9]{1,2}) +(?P<enabled>ON|OFF) +(?P<vid>[0-9]{1,4}) +(?P<priority>[0-7])"
    r"(?P<membership>[ V]+)(?P<subnet>[1-8]):LAN(?P<lan>[1-8])"
)


_VLAN_P1_ACCESS = re.compile(
    r"(?im)^[ \t%]*Permit untagged device in P1 to access router\b([^\r\n]*)$"
)


def parse_vlan_p1_untagged_access(text: str) -> bool:
    """Read the P1 untagged router-access setting, not reachability."""
    labels = _VLAN_P1_ACCESS.findall(text.replace("\r\n", "\n"))
    value = re.fullmatch(r"[ \t]*:[ \t]*(ON|OFF)[. \t]*", labels[0], re.IGNORECASE) if len(labels) == 1 else None
    if value is None:
        raise ParseError("Expected one recognised VLAN P1 untagged router-access setting")
    return value[1].upper() == "ON"


def parse_vlan_slots(text: str) -> list[dict[str, int | bool | str | list[str]]]:
    """Parse configured VLAN slots in the observed fixed-width layout."""
    header = None
    columns: dict[int, str] = {}
    slots: dict[int, dict[str, int | bool | str | list[str]]] = {}
    for raw in text.splitlines():
        line = raw.rstrip(" \t")
        if not line or re.fullmatch(r" *-{3,}", line):
            continue
        if header is None:
            header = _VLAN_HEADER.fullmatch(line)
            if header:
                # The wider 5 GHz labels place their marker two characters in.
                columns = {
                    header.start("ports") + port.start() + (2 if len(port.group()) == 4 else 0): port.group().lower()
                    for port in re.finditer(r"\S+", header["ports"])
                }
            continue
        if len(slots) == 16:
            if re.match(r" *[0-9]", line):
                raise ParseError("Unexpected additional VLAN slot row")
            continue
        if slots and re.fullmatch(PAGER_PROMPT, line.lstrip(" ")):
            continue
        row = _VLAN_ROW.fullmatch(line)
        if row is None or row.start("subnet") != header.start("subnet") or row["subnet"] != row["lan"]:
            raise ParseError("Unrecognised VLAN slot row layout")
        slot, vid = int(row["slot"]), int(row["vid"])
        if slot not in range(16) or slot in slots or vid > 4095:
            raise ParseError("Invalid or duplicate VLAN slot")
        positions = [row.start("membership") + mark.start() for mark in re.finditer("V", row["membership"])]
        if any(position not in columns for position in positions):
            raise ParseError("Misaligned VLAN membership marker")
        slots[slot] = {
            "slot": slot,
            "enabled": row["enabled"] == "ON",
            "vid": vid,
            "priority": int(row["priority"]),
            "lan": f"LAN{row['lan']}",
            "members": [columns[position] for position in positions],
        }
    if len(slots) != 16:
        raise ParseError("Incomplete VLAN slot table")
    return [slots[slot] for slot in range(16)]


_NAT_TABLE_HEADER = re.compile(r"(?:NAT )?Port Redirection Running Table[ \t]*:", re.IGNORECASE)
_NAT_TABLE_COLUMNS = re.compile(
    r"Index[ \t]+Protocol[ \t]+Public Port[ \t]+Private IP[ \t]+Private Port",
    re.IGNORECASE,
)
_NAT_REDIRECTION_ROW = re.compile(
    r"([0-9]{1,5})[ \t]+([0-9]{1,3})[ \t]+([0-9]{1,5})[ \t]+([0-9.]{1,15})[ \t]+([0-9]{1,5})"
)


def parse_nat_redirects(text: str) -> list[dict[str, int | str]]:
    """Parse the documented NAT status table, including its command echo."""
    table_header = False
    columns_header = False
    awaiting_page = False
    command_echo_seen = False
    entries: dict[int, dict[str, int | str]] = {}
    for raw in text.splitlines():
        line = raw.lstrip(" \t%").rstrip()
        if not line:
            continue
        if not table_header and not command_echo_seen and line == "> srv nat status":
            command_echo_seen = True
            continue
        if _NAT_TABLE_HEADER.fullmatch(line):
            if table_header:
                raise ParseError("Duplicate NAT redirection table header")
            table_header = True
            continue
        if _NAT_TABLE_COLUMNS.fullmatch(line):
            if not table_header or columns_header:
                raise ParseError("Unexpected NAT redirection column header")
            columns_header = True
            continue
        if entries and not awaiting_page and re.fullmatch(PAGER_PROMPT, line):
            awaiting_page = True
            continue
        row = _NAT_REDIRECTION_ROW.fullmatch(line) if columns_header else None
        if row is None:
            raise ParseError("Unrecognised NAT redirection table line")
        index, protocol, public_port, private_ip, private_port = row.groups()
        index_value = int(index)
        protocol_value = int(protocol)
        public_port_value = int(public_port)
        private_port_value = int(private_port)
        if index_value != len(entries) + 1:
            raise ParseError("Invalid, duplicate, or nonsequential NAT redirection index")
        if protocol_value > 255 or public_port_value > 65535 or private_port_value > 65535:
            raise ParseError("Invalid protocol or port in NAT redirection row")
        try:
            private_ip_value = str(IPv4Address(private_ip))
        except AddressValueError as exc:
            raise ParseError("Invalid IPv4 address in NAT redirection row") from exc
        entries[index_value] = {
            "index": index_value,
            "protocol": protocol_value,
            "public_port": public_port_value,
            "private_ip": private_ip_value,
            "private_port": private_port_value,
        }
        awaiting_page = False
    if not table_header or not columns_header or not entries or awaiting_page:
        raise ParseError("Incomplete NAT redirection table")
    return [entries[index] for index in sorted(entries)]


_DHCP_SECTION = r"LAN[1-8]|IP Routed"
_DHCP_HEADER = re.compile(r"Index[ \t]+IP Address[ \t]+MAC Address[ \t]+Leased Time[ \t]+HOST ID")
_DHCP_ROW = re.compile(
    r"(?P<index>[0-9]{1,6})[ \t]+(?P<ip>[0-9.]+)[ \t]+"
    r"(?P<mac>[0-9a-fA-F]{2}(?P<separator>[:-])[0-9a-fA-F]{2}(?:(?P=separator)[0-9a-fA-F]{2}){4})[ \t]+"
    r"(?P<time>[0-9]+:[0-5][0-9]:[0-5][0-9]|FIXED)"
    r"(?:[ \t]+(?P<host>[^\x00-\x1f\x7f]+))?"
)


def parse_dhcp_leases(text: str) -> list[dict[str, int | str | None]]:
    """Parse the DHCP lease table, keeping lease time as displayed."""
    frame = re.split(r"(?m)^[ \t]*(-{3,})[ \t]*\r?\n", text, maxsplit=1)
    if len(frame) != 3 or not re.match(rf"\s*(?:{_DHCP_SECTION})[ \t]*:[ \t]*DHCP Server\b", frame[0]):
        raise ParseError("Missing DHCP status preamble")
    sep, body = frame[1:]
    lines = [line.strip(" \t") for line in body.splitlines() if line.strip(" \t")]
    if len(lines) < 2 or not _DHCP_HEADER.fullmatch(lines[0]) or lines[1] != sep:
        raise ParseError("Missing DHCP lease table header")

    leases: list[dict[str, int | str | None]] = []
    sections: set[str] = set()
    indices: set[int] = set()
    section = None
    awaiting_page = False
    for line in lines[2:]:
        if leases and not awaiting_page and re.fullmatch(PAGER_PROMPT, line):
            awaiting_page = True
            continue
        if re.fullmatch(_DHCP_SECTION, line):
            if line in sections:
                raise ParseError("Duplicate DHCP lease section")
            sections.add(line)
            section = line
            indices.clear()
        else:
            row = _DHCP_ROW.fullmatch(line)
            if section is None or row is None:
                raise ParseError("Unrecognised DHCP lease table line")
            index = int(row["index"])
            if index < 1 or index in indices:
                raise ParseError("Invalid or duplicate DHCP lease index")
            try:
                address = str(IPv4Address(row["ip"]))
            except AddressValueError as exc:
                raise ParseError("Invalid IPv4 address in DHCP lease table") from exc
            indices.add(index)
            leases.append({
                "lan": section,
                "index": index,
                "ip_address": address,
                "mac_address": row["mac"].replace("-", ":").lower(),
                "lease_time": row["time"],
                "host_id": row["host"],
            })
        awaiting_page = False
    if awaiting_page:
        raise ParseError("Incomplete paginated DHCP lease table")
    return leases


_WAN_LINK = re.compile(r"((?:PVC_)?WAN[1-9]):[ \t]*(Online|Offline),[ \t]*stall=([YN])")


def parse_wan_links(text: str) -> list[dict[str, str | bool]]:
    """Read numbered WAN link headers, not the associated telemetry blocks."""
    links: dict[str, dict[str, str | bool]] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not re.match(r"(?:PVC_)?WAN[0-9]+\b", line):
            continue
        match = _WAN_LINK.fullmatch(line)
        if match is None or match[1] in links:
            raise ParseError("Unrecognised or duplicate numbered WAN link header")
        links[match[1]] = {"interface": match[1], "online": match[2] == "Online", "stalled": match[3] == "Y"}
    if not {"WAN1", "WAN2"} <= links.keys() or re.fullmatch(PAGER_PROMPT, text.rstrip().splitlines()[-1].strip()):
        raise ParseError("Missing or incomplete numbered WAN link status")
    return list(links.values())


def parse_lte_access(text: str) -> dict[str, str | None]:
    """Extract access technology without returning modem identifiers."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    statuses = [line for line in lines if line.startswith("Status:")]
    technologies = [line for line in lines if line.startswith("Access Tech:")]
    if len(statuses) != 1 or len(technologies) != 1:
        raise ParseError("Missing or ambiguous LTE status framing")
    match = re.fullmatch(r"Access Tech:[ \t]*(LTE|---)?", technologies[0])
    if match is None:
        raise ParseError("Unrecognised LTE access technology")
    return {"access_technology": "LTE" if match.group(1) == "LTE" else None}


_IFACE_BLOCK_RE = re.compile(
    r"Interface (?P<index>\d+) (?P<media>\S+):\s*"
    r".*?Status:\s*(?P<status>\S+)"
    r".*?IP Address:\s*(?P<ip_address>\S+)\s+Netmask:\s*(?P<netmask>\S+)"
    r".*?MAC:\s*(?P<mac>\S+)",
    re.DOTALL,
)


def parse_sys_iface(text: str) -> list[dict[str, str]]:
    """Parse documented ``sys iface`` interface blocks."""
    interfaces = []
    blocks = re.split(r"(?=Interface \d+ \S+:)", text)
    for block in blocks:
        match = _IFACE_BLOCK_RE.search(block)
        if not match:
            continue
        interfaces.append(
            {
                "interface": match.group("index"),
                "media": match.group("media"),
                "status": match.group("status"),
                "ip_address": match.group("ip_address"),
                "netmask": match.group("netmask"),
                "mac": match.group("mac"),
            }
        )
    return interfaces


_SHOW_STATUS_PATTERNS = {
    "uptime": re.compile(r"System Uptime:\s*(\S+)"),
    "primary_dns": re.compile(r"Primary DNS:\s*(\S+)"),
    "secondary_dns": re.compile(r"Secondary DNS:\s*(\S+)"),
    "lan_ip_address": re.compile(r"LAN Status.*?IP Address:\s*(\S+)", re.DOTALL),
}

_WAN_BLOCK_RE = re.compile(
    r"WAN (?P<index>\d+) Status:\s*(?P<status>\S+)\s*"
    r"Enable:\s*(?P<enable>\S+)\s+Line:\s*(?P<line>\S+)",
    re.DOTALL,
)


def parse_show_status(text: str) -> dict[str, object]:
    """Parse documented ``show status`` output into facts-shaped data."""
    result: dict[str, object] = {}
    for key, pattern in _SHOW_STATUS_PATTERNS.items():
        match = pattern.search(text)
        if match:
            result[key] = match.group(1).strip()

    result["wan"] = [
        {
            "interface": match.group("index"),
            "status": match.group("status"),
            "enable": match.group("enable"),
            "line": match.group("line"),
        }
        for match in _WAN_BLOCK_RE.finditer(text)
    ]
    return result
