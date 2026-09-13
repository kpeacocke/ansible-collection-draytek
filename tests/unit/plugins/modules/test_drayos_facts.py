from __future__ import annotations

import json
from pathlib import Path

import pytest
from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.kpeacocke.draytek.plugins.modules import drayos_facts

FIXTURES = Path(__file__).parents[3] / "fixtures" / "drayos" / "vigor2927" / "4.4.0"


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
    serialized = json.dumps({"ANSIBLE_MODULE_ARGS": args})
    basic._ANSIBLE_ARGS = to_bytes(serialized)
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
    assert drayos_facts.resolve_subsets(["all"]) == set(drayos_facts._ALL_SUBSETS)


def test_resolve_subsets_keeps_explicit_choices():
    assert drayos_facts.resolve_subsets(["interfaces", "wan"]) == {"interfaces", "wan"}


def test_commands_for_subsets_default_needs_sys_version():
    assert drayos_facts.commands_for_subsets({"default"}) == ["sys version"]


def test_commands_for_subsets_dedupes_across_subsets():
    commands = drayos_facts.commands_for_subsets({"wan", "lan", "system"})
    assert commands.count("show status") == 1
    assert "sys version" in commands


def test_build_facts_default_subset():
    responses = {"sys version": _read("sys_version.txt")}
    facts = drayos_facts.build_facts({"default"}, responses)

    assert facts["default"]["model"] == "Vigor2927Vac"
    assert facts["default"]["vendor"] == "DrayTek"


def test_build_facts_interfaces_subset():
    responses = {"sys iface": _read("sys_iface.txt")}
    facts = drayos_facts.build_facts({"interfaces"}, responses)

    assert facts["interfaces"][0]["status"] == "UP"


def test_build_facts_wan_and_lan_subsets():
    responses = {"show status": _read("show_status.txt")}
    facts = drayos_facts.build_facts({"wan", "lan"}, responses)

    assert facts["lan"]["ip_address"] == "192.168.1.1"
    assert len(facts["wan"]) >= 3


def test_module_returns_default_facts(monkeypatch):
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


def test_module_never_reports_changed_true(monkeypatch):
    monkeypatch.setattr(
        drayos_facts,
        "run_commands",
        lambda module, commands: [_read("sys_version.txt")],
    )
    _set_module_args({"gather_subset": ["all"]})

    with pytest.raises(AnsibleExitJson) as excinfo:
        drayos_facts.main()

    assert excinfo.value.kwargs["changed"] is False


def test_module_reports_connection_errors_via_fail_json(monkeypatch):
    from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.errors import (
        CommandError,
    )

    def _raise(module, commands):
        raise CommandError("device unreachable")

    monkeypatch.setattr(drayos_facts, "run_commands", _raise)
    _set_module_args({})

    with pytest.raises(AnsibleFailJson) as excinfo:
        drayos_facts.main()

    assert excinfo.value.kwargs["msg"] == "device unreachable"


def test_module_rejects_invalid_gather_subset():
    _set_module_args({"gather_subset": ["not_a_real_subset"]})

    with pytest.raises(AnsibleFailJson):
        drayos_facts.main()
