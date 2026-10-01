# Copyright: (c) 2026, kpeacocke
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Parsers for DrayOS CLI output.

The parser is validated against a sanitised Vigor2927Lac 4.5.2.2 live-device
fixture. The older Vigor2927 4.4.0 fixture remains documentation evidence.
"""
from __future__ import annotations

import re

from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.models import (
    PlatformInfo,
)

_SYS_VERSION_PATTERNS = {
    "hostname": re.compile(r"^[ \t]*Router Name:[ \t]*([^\r\n]*)", re.MULTILINE),
    "model": re.compile(r"Router Model:\s*(\S+)"),
    "version": re.compile(r"Version:\s*(\S+)"),
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
