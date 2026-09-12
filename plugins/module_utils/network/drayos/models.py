# Copyright: (c) 2026, kpeacocke
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Structured platform-identification model (engineering-specification.md, section 9).

Populating this model from real device output is deferred: DrayOS does not
have a publicly documented, collection-verified "show version" equivalent
yet. Per section 65/78 of the engineering specification, that parsing must
not be implemented until real command output has been captured from a test
device and turned into fixtures. Until then, callers receive an explicitly
"unknown" :class:`PlatformInfo` rather than guessed values.
"""
from __future__ import annotations

from dataclasses import dataclass, field

VENDOR = "DrayTek"
PLATFORM = "DrayOS"


@dataclass(frozen=True)
class PlatformInfo:
    """Structured result of DrayOS platform detection."""

    vendor: str = VENDOR
    platform: str = PLATFORM
    model: str | None = None
    firmware_version: str | None = None
    hardware_version: str | None = None
    serial_number: str | None = None
    capabilities: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, object]:
        return {
            "vendor": self.vendor,
            "platform": self.platform,
            "model": self.model,
            "firmware_version": self.firmware_version,
            "hardware_version": self.hardware_version,
            "serial_number": self.serial_number,
            "capabilities": list(self.capabilities),
        }


def unknown_platform() -> PlatformInfo:
    """Return a :class:`PlatformInfo` with no model/firmware detail populated.

    Used until command-based detection is implemented against captured
    fixtures (engineering-specification.md, section 65).
    """
    return PlatformInfo()
