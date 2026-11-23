# Copyright: (c) 2026, kpeacocke
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Structured platform-identification model (engineering-specification.md, section 9).

Fields are populated only from recognised output; absent values remain unknown.
"""
from __future__ import annotations

from dataclasses import dataclass, field

VENDOR = "DrayTek"
PLATFORM = "DrayOS"
QUALIFIED_V2927LAC_4522_READ_CAPABILITIES = (
    "platform",
    "lan_profiles",
    "ipv4_routes",
    "vlan_slots",
    "vlan_p1_untagged_access",
    "nat_redirects",
    "dhcp_leases",
    "dhcp_lease_time",
    "dhcp2_status",
    "wan_links",
    "lte_access",
)


@dataclass(frozen=True)
class PlatformInfo:
    """Structured result of DrayOS platform detection."""

    vendor: str = VENDOR
    platform: str = PLATFORM
    model: str | None = None
    firmware_version: str | None = None
    hardware_version: str | None = None
    serial_number: str | None = None
    hostname: str | None = None
    discovery_status: str = "unrecognised"
    capabilities: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, object]:
        return {
            "vendor": self.vendor,
            "platform": self.platform,
            "model": self.model,
            "hostname": self.hostname,
            "firmware_version": self.firmware_version,
            "hardware_version": self.hardware_version,
            "serial_number": self.serial_number,
            "discovery_status": self.discovery_status,
            "capabilities": list(self.capabilities),
        }


def unknown_platform() -> PlatformInfo:
    """Return a :class:`PlatformInfo` with no model/firmware detail populated.

    Used until command-based detection is implemented against captured
    fixtures (engineering-specification.md, section 65).
    """
    return PlatformInfo()
