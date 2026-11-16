from __future__ import annotations

import json
from pathlib import Path

import pytest
from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.errors import (
    CommandError,
    CommandTimeoutError,
    ConnectionError as DrayOSConnectionError,
)
from ansible_collections.kpeacocke.draytek.plugins.modules import drayos_hostname


VERSION = (
    Path(__file__).parents[3] / "fixtures/drayos/vigor2927lac/4.5.2.2/sys_version.txt"
).read_text(encoding="utf-8")


class Device:
    def __init__(self):
        self.hostname = "branch-old"
        self.calls = []
        self.errors = {}
        self.responses = {}
        self.readback = None

    def execute(self, module, commands):
        self.calls.append(commands)
        call = len(self.calls)
        if call in self.errors:
            raise self.errors[call]
        if call in self.responses:
            return self.responses[call]
        if commands == ["sys version"]:
            return [VERSION.replace("REDACTED_HOSTNAME", self.hostname)]
        assert len(commands) == 1
        assert commands[0].startswith("sys name ")
        self.hostname = self.readback or commands[0].removeprefix("sys name ")
        return [""]


@pytest.fixture
def device(monkeypatch):
    device = Device()
    monkeypatch.setattr(drayos_hostname, "run_commands", device.execute)
    return device


@pytest.fixture
def invoke(monkeypatch, capsys):
    def run(args):
        monkeypatch.setattr(basic, "_ANSIBLE_ARGS",
                            to_bytes(json.dumps({"ANSIBLE_MODULE_ARGS": args})))
        monkeypatch.setattr(basic, "_ANSIBLE_PROFILE", "legacy")
        with pytest.raises(SystemExit) as excinfo:
            drayos_hostname.main()
        result = json.loads(capsys.readouterr().out)
        assert excinfo.value.code == (1 if result.get("failed") else 0)
        return result
    return run


@pytest.mark.parametrize("desired,check_mode,changed", [
    ("branch-new", False, True),
    ("branch-old", False, False),
    ("branch-new", True, True),
    ("branch-old", True, False),
])
def test_resource_state_matrix(device, invoke, desired, check_mode, changed):
    result = invoke({"config": {"hostname": desired},
                     "_ansible_check_mode": check_mode, "_ansible_diff": True})
    assert not result.get("failed"), result
    assert result["changed"] is changed
    assert result["before"] == {"hostname": "branch-old"}
    assert result["after"] == {"hostname": desired}
    assert result["commands"] == (["sys name branch-new"] if changed else [])
    assert result["diff"] == {"before": {"hostname": "branch-old"},
                              "after": {"hostname": desired}}
    assert device.calls == (
        [["sys version"], ["sys name branch-new"], ["sys version"]]
        if changed and not check_mode else [["sys version"]]
    )
    assert device.hostname == (desired if not check_mode else "branch-old")
    assert "Router serial" not in json.dumps(result)


def test_second_identical_execution_sends_no_configuration(device, invoke):
    args = {"config": {"hostname": "branch-new"}}
    first = invoke(args)
    assert first["changed"] is True
    calls = len(device.calls)
    second = invoke(args)
    assert second["changed"] is False
    assert second["commands"] == []
    assert second["before"] == second["after"] == {"hostname": "branch-new"}
    assert device.calls[calls:] == [["sys version"]]


@pytest.mark.parametrize("check_mode", [False, True])
def test_gathered_reads_and_parsed_never_connects(device, invoke, check_mode):
    result = invoke({"state": "gathered", "_ansible_check_mode": check_mode})
    assert result["gathered"] == {"hostname": "branch-old"}
    assert result["changed"] is False
    assert device.calls == [["sys version"]]
    device.calls.clear()
    result = invoke({"state": "parsed", "running_config": VERSION,
                     "_ansible_check_mode": check_mode})
    assert result["parsed"] == {"hostname": "REDACTED_HOSTNAME"}
    assert result["changed"] is False
    assert device.calls == []


@pytest.mark.parametrize("hostname", ["a", "a" * 39, "Branch.Example_1-2"])
def test_supported_name_boundaries_are_written_and_verified(device, invoke, hostname):
    result = invoke({"config": {"hostname": hostname}})
    assert not result.get("failed"), result
    assert result["after"] == {"hostname": hostname}
    assert device.calls == [["sys version"], [f"sys name {hostname}"], ["sys version"]]


@pytest.mark.parametrize("hostname", [
    "", "a" * 40, "a b", "a\nsys reboot", "a\rsys reboot", "a;sys reboot",
    "a\x00", "a\tb", "a'b", 'a"b', "a`b", "a\\b", "-option", "rout\u00e9r",
])
def test_invalid_names_fail_before_any_device_command(device, invoke, hostname):
    result = invoke({"config": {"hostname": hostname}})
    assert result["failed"] is True
    assert result["changed"] is False
    assert "hostname must be" in result["msg"]
    assert device.calls == []


@pytest.mark.parametrize("args", [
    {}, {"config": {}},
    {"state": "gathered", "config": {"hostname": "branch-new"}},
    {"state": "merged", "config": {"hostname": "branch-new"}, "running_config": VERSION},
    {"state": "parsed"},
])
def test_invalid_state_inputs_never_contact_device(device, invoke, args):
    result = invoke(args)
    assert result["failed"] is True
    assert device.calls == []


@pytest.mark.parametrize("responses", [
    [], None, [None], [VERSION, VERSION], [""],
    [VERSION.replace("Router Name:", "Missing Name:")],
    [VERSION.replace("Router Name: REDACTED_HOSTNAME", "Router Name:")],
    [VERSION + "\nRouter Name: conflicting\n"],
    [VERSION.replace("Router Model:", "Missing Model:")],
    [VERSION.replace("Version: 4.5.2.2", "Missing: 4.5.2.2")],
    [VERSION.replace("Router Name: REDACTED_HOSTNAME", "Router Name: bad\x1bname")],
])
def test_unrecognised_current_state_fails_without_writes(device, invoke, responses):
    device.responses[1] = responses
    result = invoke({"config": {"hostname": "branch-new"}})
    assert result["failed"] is True
    assert result["changed"] is False
    assert "sys version" in result["msg"]
    assert device.calls == [["sys version"]]


@pytest.mark.parametrize("old,new", [
    ("Vigor2927Lac", "VigorAP1060C"), ("4.5.2.2", "4.4.0"),
])
@pytest.mark.parametrize("check_mode", [False, True])
def test_unqualified_platform_is_rejected_before_configuration(
    device, invoke, old, new, check_mode,
):
    device.responses[1] = [VERSION.replace(old, new)]
    result = invoke({"config": {"hostname": "branch-new"},
                     "_ansible_check_mode": check_mode})
    assert result["failed"] is True
    assert result["changed"] is False
    assert "limited to Vigor2927Lac 4.5.2.2" in result["msg"]
    assert device.calls == [["sys version"]]


@pytest.mark.parametrize("call,phase", [(1, "gather"), (2, "apply"), (3, "verification")])
@pytest.mark.parametrize("error", [CommandError, CommandTimeoutError, DrayOSConnectionError])
def test_command_failures_are_explicit_redacted_and_never_retried(
    device, invoke, call, phase, error,
):
    device.errors[call] = error("SECRET_DEVICE_OUTPUT")
    result = invoke({"config": {"hostname": "branch-new"}, "_ansible_diff": True})
    assert result["failed"] is True
    assert result["changed"] is (call > 1)
    assert f"Hostname {phase} failed" in result["msg"]
    assert "SECRET_DEVICE_OUTPUT" not in json.dumps(result)
    assert len(device.calls) == call
    assert "after" not in result
    assert "diff" not in result
    if call > 1:
        assert "device may have changed" in result["msg"]


@pytest.mark.parametrize("readback", ["branch-NEW", "truncated"])
def test_acknowledgement_without_exact_readback_is_failure(device, invoke, readback):
    device.readback = readback
    result = invoke({"config": {"hostname": "branch-new"}})
    assert result["failed"] is True
    assert result["changed"] is True
    assert "readback did not match" in result["msg"]
    assert "final state is not verified" in result["msg"]
    assert device.calls == [["sys version"], ["sys name branch-new"], ["sys version"]]
    assert "after" not in result


def test_malformed_readback_cannot_report_success(device, invoke):
    device.responses[3] = [""]
    result = invoke({"config": {"hostname": "branch-new"}})
    assert result["failed"] is True
    assert result["changed"] is True
    assert "final state is not verified" in result["msg"]
