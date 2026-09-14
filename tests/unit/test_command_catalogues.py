from __future__ import annotations

from pathlib import Path

import yaml


CATALOGUE_ROOT = Path(__file__).parents[2] / "docs" / "command-reference"
EXPECTED_CATALOGUES = {
    "draytek-vigor2927-telnet.yaml": "commands",
    "draytek-vigorap-1060c-management.yaml": "records",
    "draytek-vigorap-918r-management.yaml": "records",
    "draytek-vigorswitch-g1080-management.yaml": "records",
    "draytek-vigorswitch-p2100-g2100-telnet.yaml": "commands",
}


def load_catalogue(name: str) -> dict:
    with (CATALOGUE_ROOT / name).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_installed_catalogues_have_expected_evidence_boundaries():
    for name, collection_key in EXPECTED_CATALOGUES.items():
        catalogue = load_catalogue(name)
        assert catalogue["schema_version"]
        assert catalogue["source"]
        assert isinstance(catalogue[collection_key], list)
        assert catalogue[collection_key]


def test_catalogue_record_ids_are_unique():
    for name, collection_key in EXPECTED_CATALOGUES.items():
        records = load_catalogue(name)[collection_key]
        ids = [record["id"] for record in records]
        assert len(ids) == len(set(ids)), name


def test_catalogue_index_lists_every_installed_catalogue():
    index = (CATALOGUE_ROOT / "CATALOGUES.md").read_text(encoding="utf-8")
    for name in EXPECTED_CATALOGUES:
        assert name in index