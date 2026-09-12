from __future__ import annotations

from ansible_collections.kpeacocke.draytek.plugins.terminal.drayos import TerminalModule


def _matches(patterns, data: bytes) -> bool:
    return any(pattern.search(data) for pattern in patterns)


def test_stdout_prompt_matches_simple_prompt():
    assert _matches(TerminalModule.terminal_stdout_re, b"Vigor2960>")


def test_stdout_prompt_matches_hostname_with_hash():
    assert _matches(TerminalModule.terminal_stdout_re, b"router-1#")


def test_stdout_prompt_does_not_match_plain_output():
    assert not _matches(TerminalModule.terminal_stdout_re, b"some command output\nmore text")


def test_stdout_prompt_does_not_match_output_ending_in_bare_gt():
    # Regression: a space before '>' must not be mistaken for a prompt.
    assert not _matches(TerminalModule.terminal_stdout_re, b"threshold >")


def test_stdout_prompt_matches_with_trailing_space():
    assert _matches(TerminalModule.terminal_stdout_re, b"Vigor2960> ")


def test_stderr_matches_invalid_command():
    assert _matches(TerminalModule.terminal_stderr_re, b"Invalid command.")


def test_stderr_matches_unknown_command():
    assert _matches(TerminalModule.terminal_stderr_re, b"Unknown command")


def test_stderr_does_not_match_normal_output():
    assert not _matches(TerminalModule.terminal_stderr_re, b"WAN1 is up")
