"""Test bootstrap: make this repository importable as an Ansible collection.

Ansible collection code uses absolute imports rooted at
``ansible_collections.<namespace>.<name>``. Real collection tooling
(``ansible-test``) provides that layout automatically; for plain ``pytest``
runs we recreate it with a symlink under ``.cache/`` (already excluded from
lint/version control) and make the default user collections path available
so dependencies such as ``ansible.netcommon`` resolve too.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
NAMESPACE = "kpeacocke"
COLLECTION = "draytek"

_CACHE_COLLECTIONS_ROOT = REPO_ROOT / ".cache" / "collections"
_SELF_LINK = _CACHE_COLLECTIONS_ROOT / "ansible_collections" / NAMESPACE / COLLECTION
_USER_COLLECTIONS_ROOT = Path.home() / ".ansible" / "collections"


def _register_collection_paths() -> None:
    _SELF_LINK.parent.mkdir(parents=True, exist_ok=True)
    if not _SELF_LINK.exists():
        _SELF_LINK.symlink_to(REPO_ROOT, target_is_directory=True)

    for root in (_CACHE_COLLECTIONS_ROOT, _USER_COLLECTIONS_ROOT):
        root_str = str(root)
        if root.exists() and root_str not in sys.path:
            sys.path.insert(0, root_str)


_register_collection_paths()
