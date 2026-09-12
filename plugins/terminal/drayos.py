"""DrayOS terminal plugin.

Prompt and error-pattern detection are intentionally conservative. DrayOS CLI
prompt/error formatting has not yet been confirmed against a real device
fixture (engineering-specification.md, sections 11 and 65); the patterns
below are a generic starting point and must be tightened once fixtures are
captured.
"""
from __future__ import annotations

import re

from ansible.plugins.terminal import TerminalBase


class TerminalModule(TerminalBase):
    terminal_stdout_re = [
        re.compile(rb"[\r\n]?[\w\-.:/\[\]]+\s*[>#]\s*$"),
    ]

    terminal_stderr_re = [
        re.compile(rb"% ?[Ee]rror"),
        re.compile(rb"[Ii]nvalid (input|command)"),
        re.compile(rb"[Uu]nknown command"),
        re.compile(rb"[Cc]ommand not found"),
    ]
