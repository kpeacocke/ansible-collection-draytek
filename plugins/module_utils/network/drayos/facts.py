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
        if slot not in range(16) or slot in slots or vid > 4094:
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
