from __future__ import annotations

import json
from pathlib import Path

import pytest
from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.kpeacocke.draytek.plugins.modules import drayos_facts
from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.errors import ParseError

FIXTURES = Path(__file__).parents[3] / \
    "fixtures" / "drayos" / "vigor2927" / "4.4.0"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class AnsibleExitJson(Exception):
    def __init__(self, kwargs):
        super().__init__("exit_json")
        self.kwargs = kwargs


class AnsibleFailJson(Exception):
    def __init__(self, kwargs):
        super().__init__("fail_json")
        self.kwargs = kwargs


def _set_module_args(args: dict) -> None:
    basic._ANSIBLE_ARGS = to_bytes(json.dumps({"ANSIBLE_MODULE_ARGS": args}))
    basic._ANSIBLE_PROFILE = "legacy"


def _exit_json(*_args, **kwargs):
    kwargs.setdefault("changed", False)
    raise AnsibleExitJson(kwargs)


def _fail_json(*_args, **kwargs):
    kwargs["failed"] = True
    raise AnsibleFailJson(kwargs)


@pytest.fixture(autouse=True)
def module_helpers(monkeypatch):
    monkeypatch.setattr(basic.AnsibleModule, "exit_json", _exit_json)
    monkeypatch.setattr(basic.AnsibleModule, "fail_json", _fail_json)


def test_resolve_subsets_expands_all():
    assert drayos_facts.resolve_subsets(
        ["all"]) == set(drayos_facts._ALL_SUBSETS)


def test_commands_for_subsets_only_requests_needed_commands():
    assert drayos_facts.commands_for_subsets({"default"}) == ["sys version"]
    commands = drayos_facts.commands_for_subsets({"wan", "lan", "system"})
    assert commands == ["sys version", "show status"]


LAN_TABLE = "\r\n".join([
    "The LAN settings:",
    *[
        f"[{'V' if lan == 1 else 'X'}]LAN{lan} 192.0.2.{lan} 255.255.255.0 V 192.0.2.20 20 192.0.2.1"
        for lan in range(1, 9)
    ],
    "[X]Route 198.51.100.1 255.255.255.0 X 0.0.0.0 0 198.51.100.1",
])


@pytest.mark.parametrize("table", [
    LAN_TABLE.replace("[X]LAN8", "[X]LAN7"),
    LAN_TABLE.replace("192.0.2.8", "192.0.2.256"),
    LAN_TABLE.rsplit("\r\n", 2)[0],
])
def test_lan_profile_parser_rejects_bad_rows(table):
    with pytest.raises(ParseError):
        drayos_facts.facts_parsers.parse_lan_profiles(table)


def test_opt_in_lan_profiles_in_check_mode(monkeypatch):
    def execute(module, commands):
        assert module.check_mode
        assert commands == ["show lan"]
        return [LAN_TABLE]

    monkeypatch.setattr(drayos_facts, "run_commands", execute)
    _set_module_args({"gather_subset": [], "gather_lan_profiles": True, "_ansible_check_mode": True})
    with pytest.raises(AnsibleExitJson) as excinfo:
        drayos_facts.main()
    result = excinfo.value.kwargs
    assert not result["changed"]
    profiles = result["ansible_facts"]["drayos"]["lan_profiles"]
    assert set(profiles) == {f"LAN{lan}" for lan in range(1, 9)}
    assert profiles["LAN7"] == {
        "enabled": False, "ip_address": "192.0.2.7", "netmask": "255.255.255.0",
        "dhcp_enabled": True, "dhcp_start_ip": "192.0.2.20", "dhcp_pool_size": 20,
        "dhcp_gateway": "192.0.2.1",
    }


def test_build_facts_from_documented_fixture():
    responses = {
        "sys version": _read("sys_version.txt"),
        "sys iface": _read("sys_iface.txt"),
        "show status": _read("show_status.txt"),
    }
    result = drayos_facts.build_facts(
        set(drayos_facts._ALL_SUBSETS), responses)
    assert result["default"]["model"] == "Vigor2927Vac"
    assert result["interfaces"][0]["status"] == "UP"
    assert result["lan"]["ip_address"] == "192.168.1.1"
    assert len(result["wan"]) >= 3


ROUTE_TABLE = (
    "Codes: C - connected, S - static, R - RIP, * - default, ~ - private\r\n"
    "% C~ 192.0.2.0/ 255.255.255.0 is directly connected, LAN1\r\n"
    "S* 0.0.0.0/ 0.0.0.0 via 198.51.100.1, WAN1\r\n"
)


@pytest.mark.parametrize("check_mode", [False, True])
def test_opt_in_ipv4_routes(monkeypatch, check_mode):
    def execute(module, commands):
        assert module.check_mode == check_mode
        assert commands == ["ip route status"]
        return [ROUTE_TABLE]

    monkeypatch.setattr(drayos_facts, "run_commands", execute)
    _set_module_args({"gather_subset": [], "gather_ipv4_routes": True, "_ansible_check_mode": check_mode})
    with pytest.raises(AnsibleExitJson) as excinfo:
        drayos_facts.main()
    assert excinfo.value.kwargs["changed"] is False
    assert excinfo.value.kwargs["ansible_facts"]["drayos"]["ipv4_routes"] == [
        {"destination": "192.0.2.0/24", "flags": "C~", "next_hop": None, "interface": "LAN1"},
        {"destination": "0.0.0.0/0", "flags": "S*", "next_hop": "198.51.100.1", "interface": "WAN1"},
    ]


@pytest.mark.parametrize("table", [
    ROUTE_TABLE.split("\r\n", 1)[1],
    ROUTE_TABLE + "unrecognised route\r\n",
    ROUTE_TABLE.replace("255.255.255.0", "0.0.0.255"),
    ROUTE_TABLE.replace("192.0.2.0", "192.0.2.1"),
    ROUTE_TABLE.replace("198.51.100.1", "198.51.100.256"),
])
def test_ipv4_routes_reject_unknown_or_invalid_rows(table):
    with pytest.raises(ParseError):
        drayos_facts.facts_parsers.parse_ipv4_routes(table)


def test_ipv4_routes_allow_extra_legend_entries_but_not_unknown_route_codes():
    extended = ROUTE_TABLE.replace("~ - private", "~ - private, B - example code")
    parse = drayos_facts.facts_parsers.parse_ipv4_routes
    assert parse(extended) == parse(ROUTE_TABLE)
    with pytest.raises(ParseError):
        parse(extended.replace("S* 0.0.0.0", "B 0.0.0.0"))


def test_ipv4_routes_preserve_rows_across_the_known_pager():
    banner = "--- MORE ---   ['q': Quit, 'Enter': New Lines, 'Space Bar': Next Page] ---"
    parse = drayos_facts.facts_parsers.parse_ipv4_routes
    paged = ROUTE_TABLE.replace("S* 0.0.0.0", f"{banner}\r\nS* 0.0.0.0")
    assert parse(paged) == parse(ROUTE_TABLE)
    with pytest.raises(ParseError):
        parse(paged.replace("Next Page", "Unknown"))
    with pytest.raises(ParseError):
        parse(ROUTE_TABLE + banner + "\r\n")


VLAN_HEADER = "VLAN Enable VID  Pri   p1 p2 p3 p4 p5 s1 s2 s3 s4 5gs1 5gs2 5gs3 5gs4  subnet"
VLAN_ROWS = [
    " 3   ON       42 3".ljust(23) + "V" + " " * 38 + "V"
    if slot == 3 else f"{slot:2}   OFF       0 0"
    for slot in range(16)
]
VLAN_TABLE = "\n".join([
    "VLAN is Disable :", VLAN_HEADER,
    *(f"{row.ljust(VLAN_HEADER.index('subnet'))}2:LAN2" for row in VLAN_ROWS),
    "Permit untagged device in P1 to access router: ON",
])


def test_vlan_slot_facts_preserve_sparse_membership(monkeypatch):
    def execute(module, commands):
        assert module.check_mode
        assert commands == ["vlan status"]
        return [VLAN_TABLE]

    monkeypatch.setattr(drayos_facts, "run_commands", execute)
    _set_module_args({"gather_subset": [], "gather_vlan_slots": True, "_ansible_check_mode": True})
    with pytest.raises(AnsibleExitJson) as excinfo:
        drayos_facts.main()
    result = excinfo.value.kwargs
    assert result["changed"] is False
    slots = result["ansible_facts"]["drayos"]["vlan_slots"]
    assert [row["slot"] for row in slots] == list(range(16))
    assert slots[3] == {"slot": 3, "enabled": True, "vid": 42, "priority": 3,
                        "lan": "LAN2", "members": ["p1", "5gs3"]}
    assert slots[15]["members"] == []


@pytest.mark.parametrize(("check_mode", "include_slots", "state"), [(False, False, "ON"), (True, True, "OFF")])
def test_vlan_p1_untagged_access_facts(monkeypatch, check_mode, include_slots, state):
    def execute(module, commands):
        assert module.check_mode == check_mode
        assert commands == ["vlan status"]
        return [VLAN_TABLE.replace("access router: ON", f"access router: {state}....")]

    monkeypatch.setattr(drayos_facts, "run_commands", execute)
    _set_module_args({
        "gather_subset": [], "gather_vlan_p1_untagged_access": True,
        "gather_vlan_slots": include_slots, "_ansible_check_mode": check_mode,
    })
    with pytest.raises(AnsibleExitJson) as excinfo:
        drayos_facts.main()
    result = excinfo.value.kwargs
    assert result["changed"] is False
    facts = result["ansible_facts"]["drayos"]
    assert facts["vlan_p1_untagged_access"] is (state == "ON")
    assert ("vlan_slots" in facts) is include_slots


@pytest.mark.parametrize("footer", [
    "",
    "Permit untagged device in P1 to access router: unknown",
    "Permit untagged device in P1 to access router: ON\nPermit untagged device in P1 to access router: unknown",
])
def test_vlan_p1_untagged_access_rejects_missing_or_ambiguous_values(footer):
    with pytest.raises(ParseError, match="Expected one recognised"):
        drayos_facts.facts_parsers.parse_vlan_p1_untagged_access(VLAN_TABLE.rsplit("\n", 1)[0] + "\n" + footer)


@pytest.mark.parametrize("table", [
    VLAN_TABLE.replace("15   OFF", "14   OFF"),
    VLAN_TABLE.replace("V  ", "VV ", 1),
    VLAN_TABLE.replace("    V", "   VV", 1),
    VLAN_TABLE.replace("2:LAN2", "2:LAN3", 1),
    "\n".join(VLAN_TABLE.splitlines()[:-2]),
])
def test_vlan_slot_parser_rejects_ambiguous_or_incomplete_rows(table):
    with pytest.raises(ParseError):
        drayos_facts.facts_parsers.parse_vlan_slots(table)


def test_vlan_slot_parser_preserves_vendor_maximum_vid():
    table = VLAN_TABLE.replace("42 3  ", "4095 3", 1)
    parse = drayos_facts.facts_parsers.parse_vlan_slots
    assert parse(table)[3]["vid"] == 4095
    with pytest.raises(ParseError, match="Invalid or duplicate VLAN slot"):
        parse(table.replace("4095", "4096", 1))


DHCP_TABLE = """\
LAN1 : DHCP Server On    IP Pool: 192.0.2.10 ~ 192.0.2.20
       Default Gateway: 192.0.2.1
IP Routed : DHCP Server Off
-------------------------------------------------------------------------
Index IP Address       MAC Address           Leased Time    HOST ID
-------------------------------------------------------------------------
LAN1
1 192.0.2.10 02-00-00-00-00-01 27:04:59 example client
--- MORE ---   ['q': Quit, 'Enter': New Lines, 'Space Bar': Next Page] ---
2 192.0.2.11 02-00-00-00-00-02 0:00:02
"""


def test_dhcp_lease_parser_preserves_rows_and_optional_host_id():
    assert drayos_facts.facts_parsers.parse_dhcp_leases(DHCP_TABLE) == [
        {"lan": "LAN1", "index": 1, "ip_address": "192.0.2.10",
         "mac_address": "02:00:00:00:00:01", "lease_time": "27:04:59", "host_id": "example client"},
        {"lan": "LAN1", "index": 2, "ip_address": "192.0.2.11",
         "mac_address": "02:00:00:00:00:02", "lease_time": "0:00:02", "host_id": None},
    ]


def test_dhcp_lease_parser_preserves_fixed_rows_and_allows_empty_sections():
    parse = drayos_facts.facts_parsers.parse_dhcp_leases
    table = DHCP_TABLE.replace("0:00:02", "FIXED") + "LAN2\n"
    assert parse(table)[-1]["lease_time"] == "FIXED"
    assert parse(table.split("1 192.0.2.10", 1)[0]) == []


@pytest.mark.parametrize("check_mode", [False, True])
def test_dhcp_lease_facts_opt_in_runs_only_the_read_command(monkeypatch, check_mode):
    def execute(module, commands):
        assert module.check_mode is check_mode
        assert commands == ["srv dhcp status"]
        return [DHCP_TABLE]

    monkeypatch.setattr(drayos_facts, "run_commands", execute)
    _set_module_args({"gather_subset": [], "gather_dhcp_leases": True, "_ansible_check_mode": check_mode})
    with pytest.raises(AnsibleExitJson) as excinfo:
        drayos_facts.main()
    result = excinfo.value.kwargs
    assert result["changed"] is False
    assert list(result["ansible_facts"]["drayos"]) == ["dhcp_leases"]
    assert len(result["ansible_facts"]["drayos"]["dhcp_leases"]) == 2


@pytest.mark.parametrize("table", [
    DHCP_TABLE.replace("\nLAN1\n", "\n"),
    DHCP_TABLE.replace("192.0.2.11 02", "192.0.256.11 02"),
    DHCP_TABLE.replace("27:04:59", "27:64:59"),
    DHCP_TABLE.replace("0:00:02", "unknown-time"),
    DHCP_TABLE.replace("2 192.0.2.11", "1 192.0.2.11"),
    DHCP_TABLE.rsplit("\n", 2)[0],
])
def test_dhcp_lease_parser_rejects_malformed_or_partial_tables(table):
    with pytest.raises(ParseError):
        drayos_facts.facts_parsers.parse_dhcp_leases(table)


WAN_LINKS = """\
WAN1: Online, stall=N
 Mode: DHCP, Up Time=00:04:59
--- MORE ---   ['q': Quit, 'Enter': New Lines, 'Space Bar': Next Page] ---
WAN2: Offline, stall=Y
PVC_WAN5: Offline, stall=N
"""
LTE_ACCESS = "Status: Operational. (Online)\nAccess Tech: LTE\nIMEI: synthetic-private-value\n"


@pytest.mark.parametrize("check_mode", [False, True])
def test_wan_and_lte_facts_only_return_qualified_fields(monkeypatch, check_mode):
    def execute(module, commands):
        assert module.check_mode is check_mode
        assert commands == ["wan status", "wan lte stus"]
        return [WAN_LINKS, LTE_ACCESS]

    monkeypatch.setattr(drayos_facts, "run_commands", execute)
    _set_module_args({"gather_subset": [], "gather_wan_links": True, "gather_lte_access": True, "_ansible_check_mode": check_mode})
    with pytest.raises(AnsibleExitJson) as excinfo:
        drayos_facts.main()
    result = excinfo.value.kwargs
    assert result["changed"] is False
    assert result["ansible_facts"]["drayos"] == {
        "lte_access": {"access_technology": "LTE"},
        "wan_links": [
            {"interface": "WAN1", "online": True, "stalled": False},
            {"interface": "WAN2", "online": False, "stalled": True},
            {"interface": "PVC_WAN5", "online": False, "stalled": False},
        ],
    }


@pytest.mark.parametrize("text", ["", WAN_LINKS.replace("WAN2", "WAN1"), WAN_LINKS.replace("stall=Y", "stall=?"),
                                  WAN_LINKS + WAN_LINKS.splitlines()[2]])
def test_wan_links_reject_missing_duplicate_or_incomplete_headers(text):
    with pytest.raises(ParseError):
        drayos_facts.facts_parsers.parse_wan_links(text)


def test_lte_access_rejects_missing_or_ambiguous_or_unknown_values():
    parse = drayos_facts.facts_parsers.parse_lte_access
    assert parse(LTE_ACCESS.replace("Tech: LTE", "Tech: ---")) == {"access_technology": None}
    for text in ["Access Tech: LTE", LTE_ACCESS + "Access Tech: LTE", LTE_ACCESS.replace("Tech: LTE", "Tech: unknown")]:
        with pytest.raises(ParseError):
            parse(text)


def test_module_returns_facts_without_changed_state(monkeypatch):
    monkeypatch.setattr(
        drayos_facts,
        "run_commands",
        lambda module, commands: [_read("sys_version.txt")],
    )
    _set_module_args({})
    with pytest.raises(AnsibleExitJson) as excinfo:
        drayos_facts.main()
    result = excinfo.value.kwargs
    assert result["changed"] is False
    assert result["ansible_facts"]["drayos"]["default"]["model"] == "Vigor2927Vac"


def test_module_reports_connection_errors(monkeypatch):
    from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.errors import (
        CommandError,
    )

    def fail_commands(module, commands):
        raise CommandError("device unreachable")

    monkeypatch.setattr(drayos_facts, "run_commands", fail_commands)
    _set_module_args({})
    with pytest.raises(AnsibleFailJson) as excinfo:
        drayos_facts.main()
    assert excinfo.value.kwargs["msg"] == "device unreachable"


@pytest.mark.parametrize("check_mode", [False, True])
def test_module_all_subsets_with_lac_fixture(monkeypatch, check_mode):
    live = Path(__file__).parents[3] / "fixtures/drayos/vigor2927lac/4.5.2.2"
    responses = {
        command: (live / filename).read_text(encoding="utf-8")
        for command, filename in [
            ("sys version", "sys_version.txt"),
            ("sys iface", "sys_iface.txt"),
            ("show status", "show_status.txt"),
        ]
    }

    def execute(module, commands):
        assert module.check_mode is check_mode
        assert commands == ["sys version", "sys iface", "show status"]
        return [responses[command] for command in commands]

    monkeypatch.setattr(drayos_facts, "run_commands", execute)
    _set_module_args({"gather_subset": ["all"], "_ansible_check_mode": check_mode})
    with pytest.raises(AnsibleExitJson) as excinfo:
        drayos_facts.main()
    result = excinfo.value.kwargs
    assert result["changed"] is False
    parsed = result["ansible_facts"]["drayos"]
    assert parsed["default"]["hostname"] == "REDACTED_HOSTNAME"
    assert parsed["system"]["hostname"] == "REDACTED_HOSTNAME"
    assert parsed["default"]["model"] == "Vigor2927Lac"
    assert parsed["system"]["firmware_version"] == "4.5.2.2"
    assert len(parsed["interfaces"]) == 10
    assert len(parsed["wan"]) == 6
