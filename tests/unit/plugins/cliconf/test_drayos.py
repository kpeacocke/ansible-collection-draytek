from __future__ import annotations

import json

import pytest

from ansible_collections.kpeacocke.draytek.plugins.cliconf.drayos import Cliconf


class FakeConnection:
    """Minimal stand-in for the persistent connection used by CliconfBase."""

    def __init__(self):
        self._sent = []

    def send(self, **kwargs):
        self._sent.append(kwargs)
        return "OK"


@pytest.fixture
def cliconf():
    instance = Cliconf.__new__(Cliconf)
    instance._connection = FakeConnection()
    return instance


def test_get_device_info_reports_network_os(cliconf):
    info = cliconf.get_device_info()
    assert info["network_os"] == "drayos"


def test_get_requires_a_command(cliconf):
    with pytest.raises(ValueError):
        cliconf.get(command=None)


def test_get_rejects_unsupported_output(cliconf):
    with pytest.raises(ValueError):
        cliconf.get(command="show system", output="json")


def test_get_capabilities_returns_json(cliconf):
    result = cliconf.get_capabilities()
    assert json.loads(result)["network_api"] == "cliconf"


def test_run_commands_requires_commands(cliconf):
    with pytest.raises(ValueError):
        cliconf.run_commands(commands=None)


def test_run_commands_normalises_plain_strings(cliconf, monkeypatch):
    seen = []
    monkeypatch.setattr(cliconf, "send_command", lambda **kw: seen.append(kw) or "OK")

    result = cliconf.run_commands(commands=["show system"])

    assert result == ["OK"]
    assert seen == [{"command": "show system"}]


def test_run_commands_rejects_output_option(cliconf):
    with pytest.raises(ValueError):
        cliconf.run_commands(commands=[{"command": "show system", "output": "json"}])
