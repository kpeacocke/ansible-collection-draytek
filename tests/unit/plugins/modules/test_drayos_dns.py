import json

import pytest
from ansible.module_utils import basic

from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.errors import CommandError, ParseError
from ansible_collections.kpeacocke.draytek.plugins.modules import drayos_dns


DNS = "\r\n".join([
    "%% Domain name server settings:",
    *(line for lan in range(1, 9) for line in (
        f"% LAN{lan}   Primary DNS: 192.0.2.{lan}",
        f"% LAN{lan} Secondary DNS: [Not set]",
    )),
    "% Other subnet Primary DNS: [Not set]",
])


def test_dns_gathers_all_lans_with_unset_secondary_servers():
    assert drayos_dns.parse_lan_dns(DNS) == {
        f"LAN{lan}": {"primary": f"192.0.2.{lan}", "secondary": None} for lan in range(1, 9)
    }


@pytest.mark.parametrize("output", [
    DNS.replace("%% Domain name server settings:", ""),
    DNS.replace("% LAN8 Secondary DNS: [Not set]", ""),
    DNS + "\r\n% LAN1 Primary DNS: 192.0.2.20",
    DNS.replace("192.0.2.3", "private-value"),
    DNS.replace("% LAN4 Secondary DNS: [Not set]", "% LAN4 Secondary DNS:"),
])
def test_dns_rejects_incomplete_ambiguous_or_malformed_lan_rows(output):
    with pytest.raises(ParseError, match=r"DNS (?:response|row)") as error:
        drayos_dns.parse_lan_dns(output)
    assert "private-value" not in str(error.value)


@pytest.mark.parametrize("state", ["parsed", "gathered"])
def test_dns_check_mode_uses_only_the_read_command(monkeypatch, capsys, state):
    args = {"state": state, "_ansible_check_mode": True}
    if state == "parsed":
        args["running_config"] = DNS
    monkeypatch.setattr(basic, "_ANSIBLE_ARGS", json.dumps({"ANSIBLE_MODULE_ARGS": args}).encode())
    if hasattr(basic, "_ANSIBLE_PROFILE"):
        monkeypatch.setattr(basic, "_ANSIBLE_PROFILE", "legacy")
    requests = []

    def run(_module, commands):
        requests.extend(command["command"] for command in commands)
        return [DNS]

    monkeypatch.setattr(drayos_dns, "run_commands", run)
    with pytest.raises(SystemExit) as result:
        drayos_dns.main()
    assert result.value.code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["changed"] is False
    assert output[state]["LAN8"] == {"primary": "192.0.2.8", "secondary": None}
    assert requests == (["show dns"] if state == "gathered" else [])


@pytest.mark.parametrize("desired,check,version,lan,after,failed,changed,sets", [
    ("192.0.2.7", False, "4.5.2.2", "[X]LAN7 ", DNS, False, False, False),
    ("0.0.0.0", True, "4.5.2.2", "[X]LAN7 ", DNS, False, True, False),
    ("0.0.0.0", False, "4.5.2.2", "[X]LAN7 ", DNS.replace("192.0.2.7", "[Not set]"), False, True, True),
    ("192.0.2.53", False, "4.5.2.2", "[X]LAN7 ", DNS.replace("192.0.2.7", "192.0.2.53"), False, True, True),
    ("192.0.2.53", False, "4.5.2.2", "[X]LAN7 ", DNS.replace("192.0.2.1", "192.0.2.99"), True, True, True),
    ("192.0.2.53", False, "4.5.2.2", "[X]LAN7 ", None, True, True, True),
    ("192.0.2.53", False, "4.5.2.3", "[X]LAN7 ", DNS, True, False, False),
    ("192.0.2.53", False, "4.5.2.2", "[V]LAN7 ", DNS, True, False, False),
    ("192.0.2.53", False, "4.5.2.2", "[X]LAN7 \n[V]LAN7 ", DNS, True, False, False),
    ("192.0.2.53\nshow dns", False, "4.5.2.2", "[X]LAN7 ", DNS, True, False, False),
])
def test_dns_merge_safety(monkeypatch, capsys, desired, check, version, lan, after, failed, changed, sets):
    args = {"state": "merged", "lan": "LAN7", "primary_server": desired,
            "_ansible_check_mode": check, "_ansible_diff": True}
    monkeypatch.setattr(basic, "_ANSIBLE_ARGS", json.dumps({"ANSIBLE_MODULE_ARGS": args}).encode())
    if hasattr(basic, "_ANSIBLE_PROFILE"):
        monkeypatch.setattr(basic, "_ANSIBLE_PROFILE", "legacy")
    calls = []

    def run(_module, commands):
        request = commands[0]
        command = request if isinstance(request, str) else request["command"]
        calls.append(command)
        if command == "sys version":
            return [f"Router Model: Vigor2927Lac    Version: {version} English"]
        if command == "show lan":
            return [lan]
        if command == "show dns":
            return [DNS if calls.count(command) == 1 else after]
        if after is None:
            raise CommandError("private-device-output")
        return ["ack"]

    monkeypatch.setattr(drayos_dns, "run_commands", run)
    with pytest.raises(SystemExit) as result:
        drayos_dns.main()
    assert result.value.code == int(failed)
    output = json.loads(capsys.readouterr().out)
    assert output["changed"] is changed
    assert [cmd for cmd in calls if cmd.startswith("srv ")] == (
        [f"srv dhcp dns1 lan7 {desired}"] if sets else []
    )
    if failed:
        assert output["state_may_have_changed"] is sets
        assert "private-device-output" not in output["msg"]
    else:
        assert output["diff"]["after"] == {"primary_server": None if desired == "0.0.0.0" else desired}
        assert calls.count("show dns") == (2 if sets else 1)


@pytest.mark.parametrize("desired,check,before,after,lan,failed,changed,sets", [
    ("0.0.0.0", False, DNS, DNS, "[X]LAN7 ", False, False, False),
    ("192.0.2.54", False, DNS.replace("LAN7 Secondary DNS: [Not set]", "LAN7 Secondary DNS: 192.0.2.54"),
     DNS, "[X]LAN7 ", False, False, False),
    ("192.0.2.54", True, DNS, DNS, "[X]LAN7 ", False, True, False),
    ("192.0.2.54", False, DNS, DNS.replace("LAN7 Secondary DNS: [Not set]", "LAN7 Secondary DNS: 192.0.2.54"),
     "[X]LAN7 ", False, True, True),
    ("0.0.0.0", False, DNS.replace("LAN7 Secondary DNS: [Not set]", "LAN7 Secondary DNS: 192.0.2.54"),
     DNS, "[X]LAN7 ", False, True, True),
    ("192.0.2.54", False, DNS, DNS, "[X]LAN7 ", True, True, True),
    ("192.0.2.54", False, DNS,
     DNS.replace("LAN7 Secondary DNS: [Not set]", "LAN7 Secondary DNS: 192.0.2.54").replace("192.0.2.1", "192.0.2.99"),
     "[X]LAN7 ", True, True, True),
    ("192.0.2.54", False, DNS, None, "[X]LAN7 ", True, True, True),
    ("192.0.2.54", False, DNS, DNS, "[V]LAN7 ", True, False, False),
    ("224.0.0.1", False, DNS, DNS, "[X]LAN7 ", True, False, False),
    ("192.0.2.54\nshow dns", False, DNS, DNS, "[X]LAN7 ", True, False, False),
])
def test_secondary_dns_merge_safety(monkeypatch, capsys, desired, check, before, after, lan, failed, changed, sets):
    args = {"state": "merged", "lan": "LAN7", "secondary_server": desired,
            "_ansible_check_mode": check, "_ansible_diff": True}
    monkeypatch.setattr(basic, "_ANSIBLE_ARGS", json.dumps({"ANSIBLE_MODULE_ARGS": args}).encode())
    if hasattr(basic, "_ANSIBLE_PROFILE"):
        monkeypatch.setattr(basic, "_ANSIBLE_PROFILE", "legacy")
    calls = []

    def run(_module, commands):
        request = commands[0]
        command = request if isinstance(request, str) else request["command"]
        calls.append(command)
        if command == "sys version":
            return ["Router Model: Vigor2927Lac    Version: 4.5.2.2 English"]
        if command == "show lan":
            return [lan]
        if command == "show dns":
            return [before if calls.count(command) == 1 else after]
        if after is None:
            raise CommandError("private-device-output")
        return ["ack"]

    monkeypatch.setattr(drayos_dns, "run_commands", run)
    with pytest.raises(SystemExit) as result:
        drayos_dns.main()
    assert result.value.code == int(failed)
    output = json.loads(capsys.readouterr().out)
    assert output["changed"] is changed
    assert [cmd for cmd in calls if cmd.startswith("srv ")] == (
        [f"srv dhcp dns2 lan7 {desired}"] if sets else []
    )
    if failed:
        assert output["state_may_have_changed"] is sets
        assert "private-device-output" not in output["msg"]
    else:
        expected = None if desired == "0.0.0.0" else desired
        assert output["after"] == expected
        assert output["diff"]["after"] == {"secondary_server": expected}
        assert calls.count("show dns") == (2 if sets else 1)


@pytest.mark.parametrize("args", [
    {"state": "merged", "lan": "LAN7"},
    {"state": "merged", "lan": "LAN7", "primary_server": "192.0.2.53", "secondary_server": "192.0.2.54"},
    {"state": "gathered", "secondary_server": "192.0.2.54"},
])
def test_dns_rejects_ambiguous_or_misplaced_server_parameters(monkeypatch, capsys, args):
    monkeypatch.setattr(basic, "_ANSIBLE_ARGS", json.dumps({"ANSIBLE_MODULE_ARGS": args}).encode())
    if hasattr(basic, "_ANSIBLE_PROFILE"):
        monkeypatch.setattr(basic, "_ANSIBLE_PROFILE", "legacy")
    monkeypatch.setattr(drayos_dns, "run_commands", lambda *_args: pytest.fail("unexpected device access"))
    with pytest.raises(SystemExit) as result:
        drayos_dns.main()
    assert result.value.code == 1
    assert json.loads(capsys.readouterr().out)["failed"]
