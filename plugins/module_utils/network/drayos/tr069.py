# Copyright: (c) 2026, kpeacocke
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Read-only TR-069 formats observed on Vigor2927Lac 4.5.2.2."""
from __future__ import annotations

import re

from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos.errors import (
    ParseError,
    ValidationError,
)


_PATH = re.compile(r"InternetGatewayDevice(?:\.[A-Za-z0-9_]+)*\.?", re.ASCII)
_VALUE = re.compile(
    r"(?P<value>[^\r\n\x00-\x08\x0b-\x1f\x7f]*)\r?\n\r?\n"
    r"Flag:[ \t]*(?P<flag>[0-9a-fA-F]+)\r?\n\r?\n"
    r"Writable:[ \t]*(?P<writable>[01])(?:\r?\n)*"
)


def validate_parameter(parameter: str, query: str) -> None:
    if not isinstance(parameter, str) or not _PATH.fullmatch(parameter):
        raise ValidationError("TR-069 parameter must be a complete ASCII InternetGatewayDevice path")
    if query not in ("value", "names"):
        raise ValidationError("TR-069 query must be value or names")
    if query == "names" and not parameter.endswith("."):
        raise ValidationError("TR-069 names queries require a path ending in a dot")
    if query == "value" and (
        parameter.endswith(".") or parameter == "InternetGatewayDevice"
    ):
        raise ValidationError("TR-069 value queries require a leaf parameter")


def read_command(parameter: str, query: str) -> str:
    validate_parameter(parameter, query)
    suffix = " nextlevel" if query == "names" else ""
    return f"sys tr069 get {parameter}{suffix}"


def parse_value(output: str, parameter: str) -> dict[str, object]:
    validate_parameter(parameter, "value")
    match = _VALUE.fullmatch(output) if isinstance(output, str) else None
    if match is None:
        raise ParseError("Cannot determine an unambiguous single-line TR-069 value and metadata")
    return {
        "parameter": parameter,
        "value": match["value"],
        "flag": match["flag"],
        "writable": match["writable"] == "1",
    }


def parse_names(output: str, parameter: str) -> dict[str, object]:
    validate_parameter(parameter, "names")
    if not isinstance(output, str):
        raise ParseError("Expected text for TR-069 parameter names")
    names = []
    counts = []
    lengths = []
    for line in output.replace("\r\n", "\n").split("\n"):
        line = line.strip(" \t")
        if not line:
            continue
        count = re.fullmatch(r"Total number of parameter is[ \t]+([0-9]+)", line)
        length = re.fullmatch(r"Total content length of parameter is[ \t]+([0-9]+)", line)
        if count:
            counts.append(count[1])
        elif length:
            lengths.append(length[1])
        elif (
            _PATH.fullmatch(line) and line.startswith(parameter) and line != parameter
            and "." not in line[len(parameter):].rstrip(".")
        ):
            names.append(line)
        else:
            raise ParseError("Unrecognised or out-of-subtree TR-069 names response")
    count_matches = len(counts) == 1 and (counts[0].lstrip("0") or "0") == str(len(names))
    if not count_matches or len(lengths) > 1 or len(set(names)) != len(names):
        raise ParseError("Incomplete or ambiguous TR-069 parameter names")
    return {"parameter": parameter, "names": names, "count": len(names)}
