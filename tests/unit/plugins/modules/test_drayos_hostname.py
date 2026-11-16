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
        self.calls = []
        self.response = [VERSION]
        self.error = None

    def execute(self, module, commands):
        self.calls.append(commands)
        if self.error:
            raise self.error
        return self.response


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


@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize("args", [
    {"state": "merged", "config": {"hostname": "branch-new"}},
    {"state": "merged"},
    {"config": {"hostname": "branch-new"}},
])
def test_unqualified_configuration_is_rejected_before_device_access(device, invoke, args, check_mode):
    result = invoke({**args, "_ansible_check_mode": check_mode})
    assert result["failed"] is True
    assert device.calls == []


@pytest.mark.parametrize("check_mode", [False, True])
def test_gathered_reads_and_parsed_never_connects(device, invoke, check_mode):
    result = invoke({"state": "gathered", "_ansible_check_mode": check_mode})
    assert result["gathered"] == {"hostname": "REDACTED_HOSTNAME"}
    assert result["changed"] is False
    assert device.calls == [["sys version"]]
    device.calls.clear()
    result = invoke({"state": "parsed", "running_config": VERSION,
                     "_ansible_check_mode": check_mode})
    assert result["parsed"] == {"hostname": "REDACTED_HOSTNAME"}
    assert result["changed"] is False
    assert device.calls == []


@pytest.mark.parametrize("args", [
    {"state": "gathered", "running_config": VERSION}, {"state": "parsed"},
])
def test_invalid_state_inputs_never_contact_device(device, invoke, args):
    assert invoke(args)["failed"] is True
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
    device.response = responses
    result = invoke({"state": "gathered"})
    assert result["failed"] is True
    assert result["changed"] is False
    assert "sys version" in result["msg"]
    assert device.calls == [["sys version"]]


@pytest.mark.parametrize("error", [CommandError, CommandTimeoutError, DrayOSConnectionError])
def test_gather_failures_are_explicit_redacted_and_never_retried(device, invoke, error):
    device.error = error("SECRET_DEVICE_OUTPUT")
    result = invoke({"state": "gathered"})
    assert result["failed"] is True
    assert result["changed"] is False
    assert "Hostname gather failed" in result["msg"]
    assert "SECRET_DEVICE_OUTPUT" not in json.dumps(result)
    assert device.calls == [["sys version"]]
