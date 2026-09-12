# Copyright: (c) 2026, kpeacocke
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Exception taxonomy for the DrayOS module_utils layer.

Modules must translate these into Ansible-native failures (``fail_json``) at
the module boundary; they must never leak into playbook output containing
secrets (see engineering-specification.md, section 14).

Only the errors required by milestone 1 (connectivity) are defined here.
TR-069- and capability-specific errors are added when those features are
implemented.
"""
from __future__ import annotations


class DrayTekError(Exception):
    """Base class for all DrayTek collection errors."""


class ConnectionError(DrayTekError):
    """Raised when a connection to a DrayOS device cannot be established or is lost."""


class AuthenticationError(ConnectionError):
    """Raised when device authentication fails."""


class CommandError(DrayTekError):
    """Raised when a DrayOS command fails or returns an unexpected error response."""


class CommandTimeoutError(CommandError):
    """Raised when a DrayOS command does not complete within the configured timeout."""


class ParseError(DrayTekError):
    """Raised when DrayOS command output cannot be parsed into a structured result."""


class UnsupportedPlatformError(DrayTekError):
    """Raised when the connected device is not a supported DrayOS platform."""


class ValidationError(DrayTekError):
    """Raised when module arguments or resource configuration fail validation."""
