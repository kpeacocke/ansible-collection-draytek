from __future__ import annotations

import pytest

from ansible_collections.kpeacocke.draytek.plugins.module_utils.network.drayos import (
    errors,
)


def test_authentication_error_is_a_connection_error():
    assert issubclass(errors.AuthenticationError, errors.ConnectionError)


def test_command_timeout_error_is_a_command_error():
    assert issubclass(errors.CommandTimeoutError, errors.CommandError)


@pytest.mark.parametrize(
    "exc_type",
    [
        errors.ConnectionError,
        errors.AuthenticationError,
        errors.CommandError,
        errors.CommandTimeoutError,
        errors.ParseError,
        errors.UnsupportedPlatformError,
        errors.ValidationError,
    ],
)
def test_all_errors_derive_from_draytek_error(exc_type):
    assert issubclass(exc_type, errors.DrayTekError)


def test_error_message_is_preserved():
    exc = errors.CommandError("boom")
    assert str(exc) == "boom"
