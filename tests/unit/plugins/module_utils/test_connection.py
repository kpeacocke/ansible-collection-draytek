from __future__ import annotations

import json

import pytest

from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos import (
    connection as connection_module,
)
from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.errors import (
    CommandError,
)


class FakeModule:
    def __init__(self):
        self._socket_path = "/tmp/fake-socket"
        self.failed = None

    def fail_json(self, **kwargs):
        self.failed = kwargs
        raise SystemExit("fail_json called")


class FakeConnection:
    def __init__(self, socket_path):
        self.socket_path = socket_path

    def get_capabilities(self):
        return json.dumps({"network_api": "cliconf"})

    def run_commands(self, commands, check_rc=True):
        return [f"output for {command}" for command in commands]


@pytest.fixture(autouse=True)
def fake_connection(monkeypatch):
    monkeypatch.setattr(connection_module, "Connection", FakeConnection)


def test_get_capabilities_caches_on_module():
    module = FakeModule()
    first = connection_module.get_capabilities(module)
    second = connection_module.get_capabilities(module)
    assert first is second
    assert first["network_api"] == "cliconf"


def test_get_connection_returns_cliconf_connection():
    module = FakeModule()
    conn = connection_module.get_connection(module)
    assert isinstance(conn, FakeConnection)


def test_get_connection_fails_for_non_cliconf_api(monkeypatch):
    module = FakeModule()
    monkeypatch.setattr(
        connection_module,
        "get_capabilities",
        lambda m: {"network_api": "not-cliconf"},
    )
    with pytest.raises(SystemExit):
        connection_module.get_connection(module)
    assert module.failed is not None


def test_run_commands_returns_output():
    module = FakeModule()
    result = connection_module.run_commands(module, ["show system"])
    assert result == ["output for show system"]


def test_run_commands_wraps_connection_errors(monkeypatch):
    module = FakeModule()

    class FailingConnection(FakeConnection):
        def run_commands(self, commands, check_rc=True):
            from ansible.module_utils.connection import ConnectionError

            raise ConnectionError("boom")

    monkeypatch.setattr(connection_module, "Connection", FailingConnection)

    with pytest.raises(CommandError):
        connection_module.run_commands(module, ["show system"])
