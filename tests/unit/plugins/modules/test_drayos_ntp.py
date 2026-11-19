import json
from pathlib import Path

import pytest
from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.errors import (
    CommandError,
    CommandTimeoutError,
    ConnectionError as DrayOSConnectionError,
    ParseError,
    ValidationError,
)
from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.ntp import (
    normalise_server,
    parse_ntp,
)
from ansible_collections.kpeacocke.draytek.plugins.modules import drayos_ntp


VERSION = (
    Path(__file__).parents[3] / "fixtures/drayos/vigor2927lac/4.5.2.2/sys_version.txt"
).read_text(encoding="utf-8")
CURRENT = {"primary_server": "original.example", "secondary_server": ""}


def time_output(primary="original.example", secondary=""):
    return f"  Primary NTP Server: [{primary}]\r\n  Secondary NTP Server: [{secondary}]\r\n"


class Device:
    def __init__(self):
        self.calls = []
        self.primary = "original.example"
        self.secondary = ""
        self.version = VERSION
        self.mode = "normal"
        self.read_error = None
        self.write_error = None

    def execute(self, module, commands):
        self.calls.extend(commands)
        command = commands[0]
        if command == "sys version":
            return [self.version]
        if command == "sys time show":
            if self.read_error:
                raise self.read_error
            return [time_output(self.primary, self.secondary)]
        assert command.startswith("sys time server 1 ")
        if self.mode != "unchanged":
            self.primary = command.split()[-1]
        if self.mode == "secondary_changed":
            self.secondary = "unexpected.example"
        if self.mode == "malformed_readback":
            self.secondary = "SECRET\x1bVALUE"
        if self.mode == "readback_connection_loss":
            self.read_error = DrayOSConnectionError("SECRET_DEVICE_OUTPUT")
        if self.write_error:
            raise self.write_error
        return ["OK"]


@pytest.fixture
def device(monkeypatch):
    value = Device()
    monkeypatch.setattr(drayos_ntp, "run_commands", value.execute)
    return value


@pytest.fixture
def invoke(monkeypatch, capsys):
    def run(args):
        monkeypatch.setattr(basic, "_ANSIBLE_ARGS",
                            to_bytes(json.dumps({"ANSIBLE_MODULE_ARGS": args})))
        monkeypatch.setattr(basic, "_ANSIBLE_PROFILE", "legacy")
        with pytest.raises(SystemExit) as excinfo:
            drayos_ntp.main()
        result = json.loads(capsys.readouterr().out)
        assert excinfo.value.code == (1 if result.get("failed") else 0)
        return result
    return run


def merged(server="time.cloudflare.com", **kwargs):
    return {"state": "merged", "config": {"primary_server": server}, **kwargs}


@pytest.mark.parametrize("check", [False, True])
def test_gather_and_offline_parse_never_write(device, invoke, check):
    result = invoke({"_ansible_check_mode": check})
    assert result["changed"] is False
    assert result["gathered"] == CURRENT
    assert device.calls == ["sys time show"]
    device.calls.clear()
    result = invoke({"state": "parsed", "running_config": time_output(),
                     "_ansible_check_mode": check})
    assert result["parsed"] == CURRENT
    assert result["changed"] is False
    assert device.calls == []


def test_change_verifies_both_fields_and_second_run_sends_no_write(device, invoke):
    device.secondary = "retained.example"
    result = invoke(merged("TIME.Cloudflare.COM", _ansible_diff=True))
    expected = {"primary_server": "time.cloudflare.com", "secondary_server": "retained.example"}
    assert result["changed"] is True
    assert result["after"] == expected
    assert result["before"]["primary_server"] == "original.example"
    assert result["diff"] == {"before": result["before"], "after": expected}
    assert device.calls == [
        "sys version", "sys time show", "sys time server 1 time.cloudflare.com", "sys time show",
    ]
    device.calls.clear()
    result = invoke(merged("Time.Cloudflare.Com"))
    assert result["changed"] is False
    assert result["before"] == result["after"] == expected
    assert device.calls == ["sys version", "sys time show"]


@pytest.mark.parametrize("server,changed", [("time.cloudflare.com", True), ("ORIGINAL.EXAMPLE", False)])
def test_check_mode_predicts_without_sending_configuration(device, invoke, server, changed):
    result = invoke(merged(server, _ansible_check_mode=True, _ansible_diff=True))
    assert result["changed"] is changed
    assert result["before"] == CURRENT
    assert result["after"] == {**CURRENT, "primary_server": server.lower()}
    assert device.primary == "original.example"
    assert device.calls == ["sys version", "sys time show"]


@pytest.mark.parametrize("value", [
    "", "a\nsys reboot", "a;sys reboot", "a b", "a\tb", "'a'", "a\\b", "-a", "a-",
    "a..b", "a.", "a" * 64 + ".example", ".".join(["a" * 63] * 4), "tést.example",
])
def test_invalid_desired_names_fail_before_device_access(device, invoke, value):
    with pytest.raises(ValidationError):
        normalise_server(value)
    result = invoke(merged(value))
    assert result["failed"] is True
    assert result["changed"] is False
    assert device.calls == []


@pytest.mark.parametrize("args", [
    {"state": "merged"}, {"state": "merged", "config": {}},
    {"state": "merged", "config": {"secondary_server": "secondary.example"}},
    {"state": "parsed"}, {"state": "gathered", "config": {"primary_server": "a.example"}},
    {"state": "gathered", "running_config": time_output()},
    merged(running_config=time_output()),
])
def test_invalid_state_inputs_fail_before_device_access(device, invoke, args):
    assert invoke(args)["failed"] is True
    assert device.calls == []


@pytest.mark.parametrize("version", [
    VERSION.replace("Vigor2927Lac", "Vigor2927Vac"),
    VERSION.replace("4.5.2.2", "4.5.2.3"),
    VERSION + "\nRouter Model: Vigor2927Lac Version: 4.5.2.2\n",
    "unrecognised output",
    "Description Router Model: Vigor2927Lac\nRouter Model: Vigor2927Vac Version: 4.5.2.2\n",
    "Router Model:\nVigor2927Lac Version: 4.5.2.2\n",
    "Router Model: Vigor2927Lac Version:\n4.5.2.2\n",
    "Router Model: Vigor2927Lac\nDescription Version: 4.5.2.2\n",
])
def test_other_or_ambiguous_platforms_cannot_write(device, invoke, version):
    device.version = version
    result = invoke(merged())
    assert result["failed"] is True
    assert result["changed"] is False
    assert device.calls == ["sys version"]


@pytest.mark.parametrize("mode", [
    "unchanged", "secondary_changed", "malformed_readback", "readback_connection_loss",
])
def test_failed_readback_reports_possible_change_without_automatic_retry(device, invoke, mode):
    device.mode = mode
    result = invoke(merged())
    assert result["failed"] is True
    assert result["changed"] is True
    assert result["state_may_have_changed"] is True
    assert "independently before retrying" in result["msg"]
    assert "SECRET" not in json.dumps(result)
    assert device.calls == [
        "sys version", "sys time show", "sys time server 1 time.cloudflare.com", "sys time show",
    ]


@pytest.mark.parametrize("error", [CommandError, CommandTimeoutError, DrayOSConnectionError])
@pytest.mark.parametrize("phase", ["gather", "write"])
def test_transport_errors_are_redacted_and_preserve_uncertain_write_state(device, invoke, error, phase):
    if phase == "gather":
        device.read_error = error("SECRET_DEVICE_OUTPUT")
    else:
        device.write_error = error("SECRET_DEVICE_OUTPUT")
    result = invoke(merged())
    assert result["failed"] is True
    assert result["changed"] is (phase == "write")
    assert result["state_may_have_changed"] is (phase == "write")
    assert "SECRET_DEVICE_OUTPUT" not in json.dumps(result)
    assert device.calls == ["sys version", "sys time show"] + (
        ["sys time server 1 time.cloudflare.com"] if phase == "write" else []
    )


@pytest.mark.parametrize("output", [
    "", "Primary NTP Server: [a.example]",
    time_output() + "Primary NTP Server: [duplicate.example]\n",
    time_output() + "secondary NTP Server: [duplicate.example]\n",
    time_output().replace("[original.example]", "original.example"),
    time_output(primary="a\ninjected"), time_output(primary="a\x1b.example"),
])
def test_malformed_current_state_is_not_treated_as_an_empty_configuration(output):
    with pytest.raises(ParseError):
        parse_ntp(output)


@pytest.mark.parametrize("response", [None, [], [None], [time_output(), time_output()], ["unrecognised"]])
def test_invalid_read_responses_never_reach_a_configuration_command(monkeypatch, invoke, response):
    calls = []

    def execute(module, commands):
        calls.extend(commands)
        return [VERSION] if commands == ["sys version"] else response

    monkeypatch.setattr(drayos_ntp, "run_commands", execute)
    result = invoke(merged())
    assert result["failed"] is True
    assert result["changed"] is False
    assert calls == ["sys version", "sys time show"]


def test_dns_length_boundaries_accept_253_and_reject_254_characters():
    longest = ".".join(["a" * 63] * 3 + ["b" * 61])
    assert len(longest) == 253
    assert normalise_server(longest) == longest
    with pytest.raises(ValidationError):
        normalise_server(longest + "b")


def test_parser_preserves_explicit_empty_fields_and_normalises_dns_case():
    assert parse_ntp(time_output("TIME.Example", "SECONDARY.Example")) == {
        "primary_server": "time.example", "secondary_server": "secondary.example",
    }
    assert parse_ntp(time_output("", " ")) == {"primary_server": "", "secondary_server": ""}
