from __future__ import annotations

from pathlib import Path

import pytest

from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos import facts

FIXTURES = Path(__file__).parents[3] / \
    "fixtures" / "drayos" / "vigor2927" / "4.4.0"
LIVE_FIXTURES = Path(__file__).parents[3] / \
    "fixtures" / "drayos" / "vigor2927lac" / "4.5.2.2"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _read_live(name: str) -> str:
    return (LIVE_FIXTURES / name).read_text(encoding="utf-8")


def test_parse_sys_version_extracts_documented_platform_fields():
    info = facts.parse_sys_version(_read("sys_version.txt"))
    assert info.hostname == "DrayTek"
    assert info.model == "Vigor2927Vac"
    assert info.firmware_version == "4.4.0"
    assert info.hardware_version == "3075_6ffc5c5 drayos2015_V2927_440"
    assert info.serial_number is None


def test_parse_sys_version_leaves_unrecognised_fields_unset():
    info = facts.parse_sys_version("not a real sys version response")
    assert info.hostname is None
    assert info.model is None
    assert info.firmware_version is None


def test_parse_sys_iface_extracts_interface_blocks():
    interfaces = facts.parse_sys_iface(_read("sys_iface.txt"))
    assert interfaces[0] == {
        "interface": "0",
        "media": "Ethernet",
        "status": "UP",
        "ip_address": "192.168.1.1",
        "netmask": "0xFFFFFF00",
        "mac": "00-50-7F-00-00-00",
    }
    assert len([item for item in interfaces if item["status"] == "DOWN"]) >= 5


def test_parse_show_status_extracts_lan_and_wan_fields():
    result = facts.parse_show_status(_read("show_status.txt"))
    assert result["uptime"] == "95:4:44"
    assert result["primary_dns"] == "8.8.8.8"
    assert result["lan_ip_address"] == "192.168.1.1"
    assert result["wan"][0]["interface"] == "1"
    assert result["wan"][0]["status"] == "Disconnected"


def test_parse_sys_version_extracts_live_vigor2927lac_firmware():
    info = facts.parse_sys_version(_read_live("sys_version.txt"))

    assert info.hostname == "REDACTED_HOSTNAME"
    assert info.model == "Vigor2927Lac"
    assert info.firmware_version == "4.5.2.2"
    assert info.hardware_version == "6569_e31a944115 drayos2015_Vigor2927_452_fd593bfca2"


def test_parse_sys_iface_handles_live_output_pagination():
    interfaces = facts.parse_sys_iface(_read_live("sys_iface.txt"))

    assert [item["interface"] for item in interfaces] == [
        "0", "3", "4", "5", "6", "7", "8", "9", "10", "11"
    ]
    assert interfaces[0]["status"] == "UP"
    assert interfaces[-1]["status"] == "DOWN"


def test_parse_show_status_extracts_connected_and_usb_wans():
    result = facts.parse_show_status(_read_live("show_status.txt"))

    assert result["uptime"] == "177:30:48"
    assert [(item["interface"], item["status"], item["line"]) for item in result["wan"]] == [
        ("1", "Connected", "Ethernet"),
        ("2", "Connected", "Ethernet"),
        ("3", "Disconnected", "Ethernet"),
        ("4", "Disconnected", "Ethernet"),
        ("5", "Disconnected", "USB"),
        ("6", "Disconnected", "USB"),
    ]


@pytest.mark.parametrize("parser, expected", [(facts.parse_sys_iface, []), (facts.parse_show_status, {"wan": []})])
def test_parsers_handle_malformed_output_without_inventing_values(parser, expected):
    assert parser("garbage input") == expected


def test_empty_hostname_does_not_consume_next_line():
    assert facts.parse_sys_version("Router Name: \nRevision: abc").hostname is None
