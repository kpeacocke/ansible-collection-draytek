from __future__ import annotations

from pathlib import Path

import pytest

from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos import (
    facts,
)

FIXTURES = Path(__file__).parents[3] / "fixtures" / "drayos" / "vigor2927" / "4.4.0"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_sys_version_extracts_model_and_firmware():
    info = facts.parse_sys_version(_read("sys_version.txt"))

    assert info.model == "Vigor2927Vac"
    assert info.firmware_version == "4.4.0"
    assert info.vendor == "DrayTek"
    assert info.platform == "DrayOS"


def test_parse_sys_version_treats_none_serial_as_missing():
    info = facts.parse_sys_version(_read("sys_version.txt"))

    assert info.serial_number is None


def test_parse_sys_version_captures_revision_as_hardware_version():
    info = facts.parse_sys_version(_read("sys_version.txt"))

    assert info.hardware_version == "3075_6ffc5c5 drayos2015_V2927_440"


def test_parse_sys_version_returns_none_fields_for_unrecognised_text():
    info = facts.parse_sys_version("not a real sys version response")

    assert info.model is None
    assert info.firmware_version is None


def test_parse_sys_iface_extracts_first_interface_block():
    interfaces = facts.parse_sys_iface(_read("sys_iface.txt"))

    assert interfaces
    first = interfaces[0]
    assert first["interface"] == "0"
    assert first["media"] == "Ethernet"
    assert first["status"] == "UP"
    assert first["ip_address"] == "192.168.1.1"
    assert first["mac"] == "00-50-7F-00-00-00"


def test_parse_sys_iface_extracts_down_interfaces():
    interfaces = facts.parse_sys_iface(_read("sys_iface.txt"))

    down_interfaces = [i for i in interfaces if i["status"] == "DOWN"]
    assert len(down_interfaces) >= 5
    assert all(i["ip_address"] == "0.0.0.0" for i in down_interfaces)


def test_parse_show_status_extracts_uptime_and_dns():
    result = facts.parse_show_status(_read("show_status.txt"))

    assert result["uptime"] == "95:4:44"
    assert result["primary_dns"] == "8.8.8.8"
    assert result["secondary_dns"] == "8.8.4.4"
    assert result["lan_ip_address"] == "192.168.1.1"


def test_parse_show_status_extracts_wan_interfaces():
    result = facts.parse_show_status(_read("show_status.txt"))

    assert len(result["wan"]) >= 3
    assert result["wan"][0]["interface"] == "1"
    assert result["wan"][0]["status"] == "Disconnected"


@pytest.mark.parametrize("parser", [facts.parse_sys_iface, facts.parse_show_status])
def test_malformed_fixture_handling_returns_empty_not_error(parser):
    if parser is facts.parse_sys_iface:
        assert parser("garbage input") == []
    else:
        result = parser("garbage input")
        assert result["wan"] == []
