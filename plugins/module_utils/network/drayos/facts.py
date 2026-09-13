# Copyright: (c) 2026, kpeacocke
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Parsers for DrayOS CLI output documented in DrayTek's own Command Reference.

Each parser here is built and tested against vendor-documented example
output (docs/command-reference/draytek-vigor2927-telnet.yaml, itself sourced
from the Vigor2927 Series User's Guide V2.2, Part X). It has not yet been
confirmed against real device output (engineering-specification.md, section
65) -- treat these as validated against documentation, not hardware, until a
real capture exists.
"""
from __future__ import annotations

import re

from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.models import (
    PlatformInfo,
)

_SYS_VERSION_PATTERNS = {
    "model": re.compile(r"Router Model:\s*(\S+)"),
    "version": re.compile(r"Version:\s*(\S+)"),
    "router_ip": re.compile(r"Router IP:\s*(\S+)"),
    "netmask": re.compile(r"Netmask:\s*(\S+)"),
    "build_date": re.compile(r"Firmware Build Date/Time:\s*(.+)"),
    "router_name": re.compile(r"Router Name:\s*(.+)"),
    "revision": re.compile(r"Revision:\s*(.+)"),
    "serial_no": re.compile(r"Router serial no:\s*(.+)"),
}


def parse_sys_version(text: str) -> PlatformInfo:
    """Parse ``sys version`` output into a :class:`PlatformInfo`.

    Documented format (Vigor2927 User's Guide V2.2, Part X, "sys version"):

        Router Model: Vigor2927Vac         Version: 4.4.0 English
        ...
        Router serial no: None
    """
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
        firmware_version=values.get("version"),
        hardware_version=values.get("revision"),
        serial_number=serial,
    )


_IFACE_BLOCK_RE = re.compile(
    r"Interface (?P<index>\d+) (?P<media>\S+):\s*"
    r".*?Status:\s*(?P<status>\S+)"
    r".*?IP Address:\s*(?P<ip_address>\S+)\s+Netmask:\s*(?P<netmask>\S+)"
    r".*?MAC:\s*(?P<mac>\S+)",
    re.DOTALL,
)


def parse_sys_iface(text: str) -> list[dict[str, str]]:
    """Parse ``sys iface`` output into a list of per-interface dictionaries.

    Documented format (Vigor2927 User's Guide V2.2, Part X, "sys iface"):
    repeated ``Interface N <media>:`` blocks each with Status/IP
    Address/Netmask/MAC. Only the first IP Address/Netmask pair in each
    block is captured (the documented example shows unlabelled secondary
    address lines whose meaning is not specified in the reference).
    """
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
    """Parse ``show status`` output into a facts-shaped dictionary.

    Documented format (Vigor2927 User's Guide V2.2, Part X, "show status"):
    system uptime, LAN status block, then one block per WAN interface.
    """
    result: dict[str, object] = {}
    for key, pattern in _SHOW_STATUS_PATTERNS.items():
        match = pattern.search(text)
        if match:
            result[key] = match.group(1).strip()

    wan_interfaces = []
    for match in _WAN_BLOCK_RE.finditer(text):
        wan_interfaces.append(
            {
                "interface": match.group("index"),
                "status": match.group("status"),
                "enable": match.group("enable"),
                "line": match.group("line"),
            }
        )
    result["wan"] = wan_interfaces

    return result
