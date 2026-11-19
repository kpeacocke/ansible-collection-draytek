import json

import pytest
from ansible.module_utils import basic

from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.errors import ParseError
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
