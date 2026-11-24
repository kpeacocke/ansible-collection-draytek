"""Practical link checks for repository Markdown documentation.

Validates that relative links and link targets in tracked Markdown files
resolve to files or directories that exist in the repository, so published
documentation cannot silently point at missing content. External URLs are
not fetched; CI must stay deterministic and offline.
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess

REPO_ROOT = Path(__file__).parents[2]

_LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)\)")
_EXTERNAL = ("http://", "https://", "mailto:")


def _tracked_markdown_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    )
    return [
        REPO_ROOT / line
        for line in result.stdout.splitlines()
        if line and not line.startswith(".baseline/")
    ]


def test_relative_markdown_links_resolve():
    files = _tracked_markdown_files()
    assert files, "expected tracked Markdown files"
    broken: list[str] = []
    for md_file in files:
        text = md_file.read_text(encoding="utf-8")
        for match in _LINK.finditer(text):
            target = match.group(1)
            if target.startswith(_EXTERNAL) or target.startswith("#"):
                continue
            path_part = target.split("#", 1)[0]
            if not path_part:
                continue
            resolved = (md_file.parent / path_part).resolve()
            if not resolved.exists():
                broken.append(f"{md_file.relative_to(REPO_ROOT)}: {target}")
    assert not broken, "broken relative links:\n" + "\n".join(broken)
