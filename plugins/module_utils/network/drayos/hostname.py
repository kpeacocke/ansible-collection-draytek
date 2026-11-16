# Copyright: (c) 2026, kpeacocke
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Hostname parsing; evidence is in docs/hostname.md."""
from __future__ import annotations

import re

from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.errors import (
    ParseError,
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
