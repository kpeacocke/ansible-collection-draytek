# Copyright: (c) 2026, kpeacocke
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""NTP server parsing and validation; see docs/ntp.md for hardware evidence."""
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


def normalise_server(value: str) -> str:
    """Accept an unquoted ASCII DNS name, never CLI metacharacters."""
    if not value or len(value) > 253 or not all(
        re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
        for label in value.split(".")
    ):
        raise ValidationError("NTP server must be an ASCII DNS name with labels of 1-63 characters")
    return value.lower()


def parse_ntp(text: str) -> dict[str, str]:
    """Read both server fields, rejecting missing, malformed or duplicate labels."""
    result = {}
    for label, key in (("Primary", "primary_server"), ("Secondary", "secondary_server")):
        prefix = rf"^[ \t]*{label} NTP Server:"
        matches = re.findall(prefix + r"[ \t]*\[([^\]\r\n]*)\][ \t\r]*$", text, re.MULTILINE | re.IGNORECASE)
        if len(re.findall(prefix, text, re.MULTILINE | re.IGNORECASE)) != 1 or len(matches) != 1:
            raise ParseError("Cannot determine both unambiguous NTP server fields from sys time show")
        value = matches[0].strip(" \t")
        try:
            result[key] = normalise_server(value) if value else ""
        except ValidationError as exc:
            raise ParseError("Unrecognised NTP server value in sys time show; device output suppressed") from exc
    return result


def require_ntp_write_platform(text: str) -> None:
    """Only allow writes on the exact platform used for command qualification."""
    platform = parse_sys_version(text)
    if (
        len(re.findall(r"^[ \t]*Router Model:", text, re.MULTILINE)) != 1
        or len(re.findall(r"\bVersion:", text)) != 1
        or platform.model != "Vigor2927Lac"
        or platform.firmware_version != "4.5.2.2"
    ):
        raise UnsupportedPlatformError(
            "NTP configuration is qualified only on Vigor2927Lac firmware 4.5.2.2"
        )
