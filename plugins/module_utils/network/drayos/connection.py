"""Connection helpers shared by DrayOS modules.

This module does not implement SSH, prompt handling, or command parsing of
its own. It is a thin wrapper around the persistent ``network_cli``
connection reached through
:class:`ansible_collections.kpeacocke.draytek.plugins.cliconf.drayos.Cliconf`
(engineering-specification.md, section 13).
"""
from __future__ import annotations

import json
from typing import Any

from ansible.module_utils._text import to_text
from ansible.module_utils.connection import Connection
from ansible.module_utils.connection import ConnectionError as AnsibleConnectionError

from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.errors import (
    CommandError,
)
from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.errors import (
    ConnectionError as DrayOSConnectionError,
)


def get_capabilities(module: Any) -> dict:
    """Return (and cache on the module) the persistent connection's capabilities."""
    if hasattr(module, "_drayos_capabilities"):
        return module._drayos_capabilities

    try:
        capabilities = Connection(module._socket_path).get_capabilities()
    except AnsibleConnectionError as exc:
        raise DrayOSConnectionError(to_text(exc)) from exc

    module._drayos_capabilities = json.loads(capabilities)
    return module._drayos_capabilities


def get_connection(module: Any) -> Connection:
    """Return (and cache on the module) the persistent connection for this invocation."""
    if hasattr(module, "_drayos_connection"):
        return module._drayos_connection

    capabilities = get_capabilities(module)
    network_api = capabilities.get("network_api")
    if network_api != "cliconf":
        module.fail_json(
            msg="Invalid connection type %r; drayos modules require network_cli" % network_api
        )

    module._drayos_connection = Connection(module._socket_path)
    return module._drayos_connection


def run_commands(module: Any, commands: Any, check_rc: bool = True) -> list:
    """Execute one or more operational commands and return their raw output."""
    connection = get_connection(module)
    try:
        return connection.run_commands(commands=commands, check_rc=check_rc)
    except AnsibleConnectionError as exc:
        raise CommandError(to_text(exc)) from exc
