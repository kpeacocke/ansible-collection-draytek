"""DrayOS cliconf plugin.

Provides the primary ``network_cli`` abstraction for DrayOS devices
(engineering-specification.md, section 12). Milestone 1 implements generic
command execution and capability negotiation only; DrayOS-specific
device-info parsing is deferred until real command output has been captured
from a test device (section 65) rather than guessed.
"""
from __future__ import annotations

import json
from collections.abc import Mapping

from ansible.errors import AnsibleConnectionFailure
from ansible.plugins.cliconf import CliconfBase

from ansible_collections.ansible.netcommon.plugins.module_utils.network.common.utils import (
    to_list,
)


class Cliconf(CliconfBase):
    def get_device_info(self):
        return {
            "network_os": "drayos",
            "network_os_version": None,
            "network_os_model": None,
            "network_os_hostname": None,
        }

    def get_capabilities(self):
        result = super(Cliconf, self).get_capabilities()
        return json.dumps(result)

    def get_config(self, source="running", flags=None, format=None):
        raise NotImplementedError(
            "drayos cliconf does not implement configuration retrieval; DrayOS "
            "command semantics for this have not been validated against a "
            "real device (engineering-specification.md, section 12)"
        )

    def edit_config(self, candidate=None, commit=True, replace=None, diff=False, comment=None):
        raise NotImplementedError(
            "drayos cliconf does not implement Cisco-style configuration mode; "
            "DrayOS does not expose an equivalent that has been validated "
            "(engineering-specification.md, section 12)"
        )

    def get(
        self,
        command=None,
        prompt=None,
        answer=None,
        sendonly=False,
        output=None,
        newline=True,
        check_all=False,
    ):
        if not command:
            raise ValueError("must provide value of command to execute")
        if output:
            raise ValueError("'output' value %s is not supported for get" % output)

        return self.send_command(
            command=command,
            prompt=prompt,
            answer=answer,
            sendonly=sendonly,
            newline=newline,
            check_all=check_all,
        )

    def run_commands(self, commands=None, check_rc=True):
        if commands is None:
            raise ValueError("'commands' value is required")

        responses = []
        for cmd in to_list(commands):
            if not isinstance(cmd, Mapping):
                cmd = {"command": cmd}
            else:
                cmd = dict(cmd)

            output = cmd.pop("output", None)
            if output:
                raise ValueError("'output' value %s is not supported for run_commands" % output)

            try:
                out = self.send_command(**cmd)
            except AnsibleConnectionFailure as exc:
                if check_rc:
                    raise
                out = getattr(exc, "message", str(exc))

            responses.append(out)

        return responses
