import json

import pytest
from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.errors import (
    CommandError,
    ParseError,
    ValidationError,
)
from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.tr069 import (
    parse_names,
    parse_value,
    read_command,
)
from ansible_collections.kpeacocke.draytek.plugins.modules import drayos_tr069


ROOT = "InternetGatewayDevice.DeviceInfo."
LEAF = ROOT + "Manufacturer"
VALUE = "DrayTek\n\nFlag: 3022\n\nWritable: 0"
NAMES = (
    "Total number of parameter is 2\r\n"
    "Total content length of parameter is 99\r\n"
    f"{LEAF}\r\n{ROOT}ModelName\r\n"
)


@pytest.mark.parametrize("value", ["DrayTek", "", "  meaningful \t ", "prefix: value", "\u79d8\u5bc6"])
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_values_preserve_text_and_explicit_empty_framing(value, newline):
    output = f"{value}{newline}{newline}Flag: 9022{newline}{newline}Writable: 0{newline}"
    assert parse_value(output, LEAF) == {
        "parameter": LEAF, "value": value, "flag": "9022", "writable": False,
    }


@pytest.mark.parametrize("output", [
    "", "DrayTek", "Flag: 3022\n\nWritable: 0",
    VALUE + "\nSECRET", VALUE.replace("Writable: 0", "Writable: 2"),
    VALUE.replace("Flag: 3022", "Flag: ?"), VALUE.replace("\n\nWritable", "\nWritable"),
    "multi\nline\n\nFlag: 3022\n\nWritable: 0", "\x00" + VALUE,
    VALUE + "\n\nWritable: 0",
])
def test_incomplete_or_ambiguous_values_fail_without_echoing_output(output):
    with pytest.raises(ParseError) as error:
        parse_value(output, LEAF)
    assert "SECRET" not in str(error.value)


def test_names_validate_count_uniqueness_and_subtree():
    assert parse_names(NAMES, ROOT) == {
        "parameter": ROOT, "names": [LEAF, ROOT + "ModelName"], "count": 2,
    }
    empty = "Total number of parameter is 0\nTotal content length of parameter is 0"
    assert parse_names(empty, ROOT)["names"] == []


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_names_accept_the_observed_count_trailer_without_a_length_header(newline):
    output = newline.join([LEAF, "", ROOT + "ModelName", "", "", "Total number of parameter is 2"])
    assert parse_names(output, ROOT) == {
        "parameter": ROOT, "names": [LEAF, ROOT + "ModelName"], "count": 2,
    }


@pytest.mark.parametrize("output", [
    "", NAMES.replace("is 2", "is 3"), NAMES + LEAF,
    NAMES.replace(ROOT + "ModelName", LEAF),
    NAMES.replace(ROOT + "ModelName", "InternetGatewayDevice.Other.Name"),
    NAMES + "\n--- MORE ---", NAMES + "\nSECRET",
    NAMES + "\nTotal number of parameter is 2",
    NAMES + "\nTotal content length of parameter is 99",
    NAMES.replace("Total content length", "Unknown content length"),
    NAMES.replace("\r\n", "\v"),
    NAMES.replace(ROOT + "ModelName", ROOT + "Object.NestedName"),
    NAMES.replace("is 2", "is " + "9" * 5000),
])
def test_names_fail_closed_on_truncation_duplicates_and_unrecognised_lines(output):
    with pytest.raises(ParseError):
        parse_names(output, ROOT)


@pytest.mark.parametrize("parameter,query", [
    (LEAF + "; sys reboot", "value"), (LEAF + "\nsys reboot", "value"),
    (LEAF + " ", "value"), (LEAF + "\t", "value"), ("Int.DeviceInfo.Name", "value"),
    (ROOT + "tést", "value"), (ROOT + ".Name", "value"), (ROOT, "value"),
    ("InternetGatewayDevice", "value"), (LEAF, "names"), (ROOT, "set"),
])
def test_invalid_paths_cannot_generate_commands(parameter, query):
    with pytest.raises(ValidationError):
        read_command(parameter, query)


@pytest.fixture
def invoke(monkeypatch, capsys):
    def run(args):
        monkeypatch.setattr(basic, "_ANSIBLE_ARGS",
                            to_bytes(json.dumps({"ANSIBLE_MODULE_ARGS": {"_ansible_no_log": True, **args}})))
        monkeypatch.setattr(basic, "_ANSIBLE_PROFILE", "legacy")
        with pytest.raises(SystemExit) as excinfo:
            drayos_tr069.main()
        result = json.loads(capsys.readouterr().out)
        assert excinfo.value.code == (1 if result.get("failed") else 0)
        return result
    return run


@pytest.mark.parametrize("check", [False, True])
@pytest.mark.parametrize("query,parameter,response", [
    ("value", LEAF, VALUE), ("names", ROOT, NAMES),
])
def test_gather_and_parse_are_private_and_never_send_writes(
    monkeypatch, invoke, check, query, parameter, response,
):
    calls = []

    def execute(module, commands):
        calls.extend(commands)
        assert module.no_log is True
        return [response]

    monkeypatch.setattr(drayos_tr069, "run_commands", execute)
    args = {"parameter": parameter, "query": query, "_ansible_check_mode": check}
    result = invoke(args)
    assert result["changed"] is False
    assert calls[0]["command"] == f"sys tr069 get {parameter}" + (
        " nextlevel" if query == "names" else ""
    )
    if query == "names":
        assert calls[0]["check_all"] is True
        assert calls[0]["newline"] is False
        assert calls[0]["answer"] == [" "] * 64
        assert len(calls[0]["prompt"]) == 64
    else:
        assert calls == [{"command": f"sys tr069 get {LEAF}"}]
    calls.clear()
    parsed = invoke({**args, "state": "parsed", "running_config": response})
    assert parsed["parsed"] == result["gathered"]
    assert parsed["changed"] is False
    assert calls == []


@pytest.mark.parametrize("args", [
    {"parameter": LEAF + ";sys reboot"},
    {"parameter": LEAF, "state": "merged"},
    {"parameter": ROOT, "query": "value"},
    {"parameter": LEAF, "running_config": VALUE},
    {"parameter": LEAF, "state": "parsed"},
])
def test_invalid_module_input_fails_without_connecting(monkeypatch, invoke, args):
    def execute(*args, **kwargs):
        pytest.fail("Invalid input attempted device access")

    monkeypatch.setattr(drayos_tr069, "run_commands", execute)
    assert invoke(args)["failed"] is True


@pytest.mark.parametrize("response", [None, [], ["a", "b"], [None], [VALUE + "\nSECRET"]])
def test_bad_transport_response_fails_without_raw_output(monkeypatch, invoke, response):
    monkeypatch.setattr(drayos_tr069, "run_commands", lambda *args: response)
    result = invoke({"parameter": LEAF})
    assert result["failed"] is True
    assert result["changed"] is False
    assert "SECRET" not in result["msg"]


def test_transport_errors_are_explicit_and_redacted(monkeypatch, invoke):
    def execute(*args):
        raise CommandError("SECRET_DEVICE_OUTPUT")

    monkeypatch.setattr(drayos_tr069, "run_commands", execute)
    result = invoke({"parameter": LEAF})
    assert result["failed"] is True
    assert result["changed"] is False
    assert result["msg"] == "TR-069 read failed (CommandError); device output suppressed"


def test_missing_task_privacy_fails_before_device_access(monkeypatch, invoke):
    def execute(*args):
        pytest.fail("Unprotected invocation queried the router")

    monkeypatch.setattr(drayos_tr069, "run_commands", execute)
    result = invoke({"parameter": LEAF, "_ansible_no_log": False})
    assert result["failed"] is True
    assert result["changed"] is False
    assert result["msg"] == "TR-069 requires task-level no_log: true before reading parameter data"
