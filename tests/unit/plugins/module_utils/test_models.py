from __future__ import annotations

from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos import (
    models,
)


def test_unknown_platform_has_expected_vendor_and_platform():
    info = models.unknown_platform()
    assert info.vendor == "DrayTek"
    assert info.platform == "DrayOS"


def test_unknown_platform_leaves_detail_fields_unset():
    info = models.unknown_platform()
    assert info.model is None
    assert info.firmware_version is None
    assert info.hardware_version is None
    assert info.serial_number is None
    assert info.capabilities == ()


def test_as_dict_round_trips_all_fields():
    info = models.PlatformInfo(
        model="Vigor2960",
        firmware_version="4.4.3",
        hardware_version="A1",
        serial_number="1234567890",
        capabilities=("TR069_GET", "TR069_SET"),
    )
    data = info.as_dict()
    assert data == {
        "vendor": "DrayTek",
        "platform": "DrayOS",
        "model": "Vigor2960",
        "firmware_version": "4.4.3",
        "hardware_version": "A1",
        "serial_number": "1234567890",
        "capabilities": ["TR069_GET", "TR069_SET"],
    }
