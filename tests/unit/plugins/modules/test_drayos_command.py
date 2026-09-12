from __future__ import annotations

import json

import pytest
from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.kpeacocke.draytek.plugins.modules import drayos_command


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


def test_returns_changed_false_and_stdout(monkeypatch):
    monkeypatch.setattr(
        drayos_command,
        "run_commands",
        lambda module, commands: ["system uptime: 3 days"],
    )
    _set_module_args({"commands": ["show system"]})

    with pytest.raises(AnsibleExitJson) as excinfo:
        drayos_command.main()

    result = excinfo.value.kwargs
    assert result["changed"] is False
    assert result["stdout"] == ["system uptime: 3 days"]
    assert result["stdout_lines"] == [["system uptime: 3 days"]]


def test_requires_commands_argument():
    _set_module_args({})

    with pytest.raises(AnsibleFailJson):
        drayos_command.main()


def test_wait_for_condition_not_met_fails(monkeypatch):
    monkeypatch.setattr(
        drayos_command,
        "run_commands",
        lambda module, commands: ["nothing relevant"],
    )
    _set_module_args(
        {
            "commands": ["show system"],
            "wait_for": ['result[0] contains "unlikely-string"'],
            "retries": 1,
            "interval": 0,
        }
    )

    with pytest.raises(AnsibleFailJson) as excinfo:
        drayos_command.main()

    assert "failed_conditions" in excinfo.value.kwargs


def test_check_mode_rejects_non_show_commands(monkeypatch):
    monkeypatch.setattr(
        drayos_command,
        "run_commands",
        lambda module, commands: pytest.fail("run_commands must not execute in this test"),
    )
    _set_module_args({"commands": ["reboot"], "_ansible_check_mode": True})

    with pytest.raises(AnsibleFailJson) as excinfo:
        drayos_command.main()

    assert "only show commands are supported" in excinfo.value.kwargs["msg"]


def test_command_error_is_reported_via_fail_json(monkeypatch):
    from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.errors import (
        CommandError,
    )

    def _raise(module, commands):
        raise CommandError("device unreachable")

    monkeypatch.setattr(drayos_command, "run_commands", _raise)
    _set_module_args({"commands": ["show system"]})

    with pytest.raises(AnsibleFailJson) as excinfo:
        drayos_command.main()

    assert excinfo.value.kwargs["msg"] == "device unreachable"


def test_wait_for_unknown_operator_fails_cleanly():
    _set_module_args(
        {
            "commands": ["show system"],
            "wait_for": ["result[0] not_a_real_operator 1"],
        }
    )

    with pytest.raises(AnsibleFailJson) as excinfo:
        drayos_command.main()

    assert "unknown operator" in excinfo.value.kwargs["msg"]


def test_wait_for_malformed_condition_fails_cleanly():
    _set_module_args({"commands": ["show system"], "wait_for": ["result[0]"]})

    with pytest.raises(AnsibleFailJson):
        drayos_command.main()


def test_retries_below_one_is_rejected():
    _set_module_args({"commands": ["show system"], "retries": 0})

    with pytest.raises(AnsibleFailJson) as excinfo:
        drayos_command.main()

    assert "retries must be at least 1" in excinfo.value.kwargs["msg"]


def test_negative_interval_is_rejected():
    _set_module_args({"commands": ["show system"], "interval": -1})

    with pytest.raises(AnsibleFailJson) as excinfo:
        drayos_command.main()

    assert "interval must not be negative" in excinfo.value.kwargs["msg"]


def test_output_key_is_stripped_from_per_command_dict(monkeypatch):
    seen = {}

    def _capture(module, commands):
        seen["commands"] = commands
        return ["ok"]

    monkeypatch.setattr(drayos_command, "run_commands", _capture)
    _set_module_args({"commands": [{"command": "show system", "output": "json"}]})

    with pytest.raises(AnsibleExitJson):
        drayos_command.main()

    assert "output" not in seen["commands"][0]
