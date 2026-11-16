# Copyright: (c) 2026, kpeacocke
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Hostname parsing and command generation; evidence is in docs/hostname.md."""
from __future__ import annotations

import re

from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.errors import (
    ParseError,
    UnsupportedPlatformError,
    ValidationError,
)
from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.facts import (
    parse_sys_version,
)


def parse_hostname(text: str) -> dict[str, str]:
    """Extract one unambiguous, populated router name from sys version."""
    platform = parse_sys_version(text)
    if (
        len(re.findall(r"^[ \t]*Router Name:", text, re.MULTILINE)) != 1
        or not platform.hostname
        or not platform.model
        or not platform.firmware_version
        or any(ord(char) < 32 or ord(char) == 127 for char in platform.hostname)
    ):
        raise ParseError("Cannot determine an unambiguous hostname from sys version")
    return {"hostname": platform.hostname}


def validate_hostname_platform(text: str) -> None:
    """Do not extend the initial configuration scope to unqualified platforms."""
    platform = parse_sys_version(text)
    if (platform.model, platform.firmware_version) != ("Vigor2927Lac", "4.5.2.2"):
        raise UnsupportedPlatformError(
            "Hostname configuration is currently limited to Vigor2927Lac 4.5.2.2"
        )


def build_hostname_command(hostname: str) -> str:
    """Accept only a single CLI token that remains compatible with our prompt."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,38}", hostname):
        raise ValidationError(
            "hostname must be 1-39 ASCII letters, digits, dots, underscores or "
            "hyphens, beginning with a letter or digit"
        )
    return f"sys name {hostname}"
