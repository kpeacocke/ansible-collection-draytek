# Copyright: (c) 2026, kpeacocke
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""DrayOS cliconf plugin.

Provides the primary ``network_cli`` abstraction for DrayOS devices
(engineering-specification.md, section 12). Milestone 1 implements generic
command execution and capability negotiation only; DrayOS-specific
device-info parsing is deferred until real command output has been captured
from a test device (section 65) rather than guessed.
"""
from __future__ import annotations

DOCUMENTATION = r"""
author: kpeacocke (@kpeacocke)
name: drayos
short_description: Use network_cli cliconf plugin with DrayOS devices
description:
  - This cliconf plugin provides low-level abstraction APIs for sending and
    receiving CLI commands from DrayOS network devices over a
    C(network_cli) connection.
  - It does not implement configuration retrieval or editing; DrayOS does
    not expose a Cisco-style configuration mode that has been validated
    against a real device.
version_added: "0.1.0"
"""

import json
from collections.abc import Mapping

from ansible.errors import AnsibleConnectionFailure
from ansible.plugins.cliconf import CliconfBase

from ansible_collections.ansible.netcommon.plugins.module_utils.network.common.utils import (
    to_list,
)
from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.connection import (
    MAX_PAGE_ADVANCES,
    PAGER_PROMPT,
)

PAGED_COMMANDS = frozenset((
    "sys iface", "show status", "show lan", "show nat", "show openport", "ip route status", "vlan status",
    "srv dhcp status", "srv nat status", "wan status", "wan lte stus",
))


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

    def _require_private_lte_read(self, command):
        if command.strip() == "wan lte stus" and self._connection.get_option("persistent_log_messages"):
            raise AnsibleConnectionFailure("LTE access reads require ansible_persistent_log_messages=false")

    def _require_private_nat_read(self, command):
        if command.strip() in {"show nat", "show openport", "srv nat status"} and \
                self._connection.get_option("persistent_log_messages"):
            raise AnsibleConnectionFailure("NAT redirection reads require ansible_persistent_log_messages=false")

    def _require_private_read(self, command):
        command = command.strip()
        if command.startswith("sys tr069 get ") and self._connection.get_option("persistent_log_messages"):
            raise AnsibleConnectionFailure("TR-069 reads require ansible_persistent_log_messages=false")
        if command == "srv dhcp status" and self._connection.get_option("persistent_log_messages"):
            raise AnsibleConnectionFailure("DHCP lease reads require ansible_persistent_log_messages=false")
        self._require_private_lte_read(command)
        self._require_private_nat_read(command)

    def get(
        self,
        command=None,
        prompt=None,
        answer=None,
        sendonly=False,
        newline=True,
        output=None,
        check_all=False,
    ):
        if not command:
            raise ValueError("must provide value of command to execute")
        if output:
            raise ValueError("'output' value %s is not supported for get" % output)

        self._require_private_read(command)
        response = self.send_command(
            command=command,
            prompt=prompt,
            answer=answer,
            sendonly=sendonly,
            newline=newline,
            check_all=check_all,
        )
        if response is None or isinstance(response, (bytes, bytearray)) and len(response) == 0:
            raise AnsibleConnectionFailure("Command execution returned no response")
        if isinstance(response, str) and not response.strip():
            raise AnsibleConnectionFailure("Command execution returned an empty response")
        return response

    def run_commands(self, commands=None, check_rc=True):
        if commands is None:
            raise ValueError("'commands' value is required")
        if self._connection.get_option("single_user_mode"):
            raise AnsibleConnectionFailure(
                "DrayOS does not support command caching; "
                "set ansible_network_single_user_mode=false for fresh readback"
            )

        responses = []
        for cmd in to_list(commands):
            if not isinstance(cmd, Mapping):
                cmd = {"command": cmd}
            else:
                cmd = dict(cmd)

            output = cmd.pop("output", None)
            if output:
                raise ValueError("'output' value %s is not supported for run_commands" % output)

            self._require_private_read(cmd.get("command", ""))

            if cmd.get("command", "").strip() in PAGED_COMMANDS and not cmd.get("prompt"):
                # check_all consumes one prompt/answer pair per page. A single
                # prompt handles only the first page in network_cli. Fresh lists
                # are essential because the receive loop mutates them in place.
                # The persistent command timeout also bounds stalled/over-limit output.
                cmd.update(prompt=[PAGER_PROMPT] * MAX_PAGE_ADVANCES,
                           answer=[" "] * MAX_PAGE_ADVANCES,
                           newline=False, check_all=True)

            try:
                out = self.send_command(**cmd)
            except AnsibleConnectionFailure as exc:
                if check_rc:
                    raise
                out = getattr(exc, "message", str(exc))

            if out is None or isinstance(out, (bytes, bytearray)) and len(out) == 0:
                raise AnsibleConnectionFailure("Command execution returned no response")
            if isinstance(out, str) and not out.strip():
                raise AnsibleConnectionFailure("Command execution returned an empty response")
            responses.append(out)

        return responses
