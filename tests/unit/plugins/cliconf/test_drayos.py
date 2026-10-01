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


@pytest.mark.parametrize("backend", ["paramiko", "libssh"])
@pytest.mark.parametrize("command", ["sys iface", "show status"])
def test_pager_advances_multiple_pages_through_network_cli(cliconf, monkeypatch, backend, command):
    from ansible_collections.ansible.netcommon.plugins.connection.network_cli import Connection
    from ansible_collections.kpeacocke.draytek.plugins.terminal.drayos import TerminalModule

    marker = b"--- MORE ---   ['q': Quit, 'Enter': New Lines, 'Space Bar': Next Page] ---\r\n"

    class PagedShell:
        def __init__(self):
            self.sent = []
            self.chunks = [b"page one\r\n" + marker, b"\r\npage two\r\n" + marker,
                           b"\r\npage three\r\nrouter>  "]
            self.read_count = 0

        def settimeout(self, timeout):
            pass

        def sendall(self, data):
            assert data == b" "  # No CR: Enter requests lines rather than a page.
            self.sent.append(data)

        def recv(self, size):
            assert len(self.sent) == self.read_count
            self.read_count += 1
            return self.chunks.pop(0)

        def read_bulk_response(self):
            return self.recv(256)

    connection = Connection.__new__(Connection)
    shell = PagedShell()
    connection._ssh_shell = shell
    connection._terminal_stdout_re = TerminalModule.terminal_stdout_re
    connection._terminal_stderr_re = TerminalModule.terminal_stderr_re
    connection._window_count = 0
    connection._buffer_read_timeout = 0
    monkeypatch.setattr(connection, "get_option", lambda option: 10)
    monkeypatch.setattr(connection, "_log_messages", lambda message: None)
    monkeypatch.setattr(connection, "_strip", lambda data: data)
    monkeypatch.setattr(connection, "_read_post_command_prompt_match", lambda: b"")

    def receive(**kwargs):
        return getattr(connection, "receive_" + backend)(
            command=kwargs["command"].encode(), prompts=kwargs["prompt"],
            answer=kwargs["answer"], newline=kwargs["newline"], check_all=kwargs["check_all"])

    monkeypatch.setattr(cliconf, "send_command", receive)
    result = cliconf.run_commands([command])[0]
    assert b"page one" in result and b"page two" in result and b"page three" in result
    assert shell.sent == [b" ", b" "]


def test_pager_does_not_override_explicit_prompt(cliconf, monkeypatch):
    seen = []
    monkeypatch.setattr(cliconf, "send_command", lambda **kw: seen.append(kw) or "OK")
    command = {"command": "sys iface", "prompt": "custom", "answer": "x"}
    cliconf.run_commands([command])
    assert seen == [command]
