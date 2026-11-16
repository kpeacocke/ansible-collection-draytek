import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts._project_factory.local import values


REPO_ROOT = Path(__file__).parents[2]
SCRIPT_ROOTS = [
    REPO_ROOT / "scripts",
    REPO_ROOT / ".baseline/catalog/common/scripts",
]


@pytest.fixture(params=SCRIPT_ROOTS, ids=["installed", "catalogue"])
def factory(request, monkeypatch):
    package_root = request.param / "_project_factory"
    name = "_review_test_factory"
    spec = importlib.util.spec_from_file_location(name, package_root / "__init__.py")
    package = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, package)
    spec.loader.exec_module(package)
    for submodule in ("common", "local"):
        module_name = f"{name}.{submodule}"
        spec = importlib.util.spec_from_file_location(module_name, package_root / f"{submodule}.py")
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, module_name, module)
        spec.loader.exec_module(module)
        setattr(package, submodule, module)
    return package


def test_existing_project_without_openssf_registration_has_no_badge_url():
    rendered = values(
        profile="ansible",
        owner="kpeacocke",
        name="ansible-collection-draytek",
        description="",
        source_repository="kpeacocke/engineering-baseline-template",
        openssf_project="",
    )

    assert rendered["OPENSSF_PROJECT"] == ""
    assert rendered["OPENSSF_PROJECT_ID"] == ""


@pytest.mark.parametrize("registration", ["", "  ", "12345", "https://www.bestpractices.dev/en/projects/12345"])
def test_factory_badge_values(factory, registration):
    rendered = factory.local.values("generic", "owner", "project", "", "owner/template", registration)
    expected_id = "12345" if registration.strip() else ""
    expected_url = f"https://www.bestpractices.dev/en/projects/{expected_id}" if expected_id else ""
    assert rendered["OPENSSF_PROJECT"] == expected_url
    assert rendered["OPENSSF_PROJECT_ID"] == expected_id


def test_factory_rejects_invalid_badge_registration(factory):
    with pytest.raises(factory.common.FactoryError, match="OpenSSF project entry"):
        factory.local.values("generic", "owner", "project", "", "owner/template", "invalid")


@pytest.mark.parametrize("destination", ["project", "generated/project"])
def test_seed_excludes_destination_at_any_depth(factory, tmp_path, destination):
    source = tmp_path / "source"
    source.mkdir()
    (source / "template.txt").write_text("template", encoding="utf-8")
    (source / ".git").mkdir()
    (source / ".git/source-only").write_text("source metadata", encoding="utf-8")
    target = source / destination
    (target / ".git").mkdir(parents=True)
    (target / ".git/HEAD").write_text("destination metadata", encoding="utf-8")

    factory.common.seed_from_source(source, target)

    assert (target / "template.txt").read_text(encoding="utf-8") == "template"
    assert (target / ".git/HEAD").read_text(encoding="utf-8") == "destination metadata"
    assert not (target / ".git/source-only").exists()
    assert not (target / destination).exists()


@pytest.mark.parametrize("script_root", SCRIPT_ROOTS, ids=["installed", "catalogue"])
def test_legacy_state_supports_doctor_reconcile_and_recovery(script_root, tmp_path):
    root = tmp_path / "legacy"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    shutil.copyfile(script_root / "baseline.py", scripts / "baseline.py")
    baseline = root / ".baseline"
    (baseline / "catalog").mkdir(parents=True)
    (baseline / "VERSION").write_text("0.5.0\n", encoding="utf-8")
    (baseline / "state.json").write_text(json.dumps({
        "installed_version": "0.5.0", "profile": "generic",
        "project_name": "legacy", "owner": "owner",
    }), encoding="utf-8")
    (baseline / "manifest.json").write_text(json.dumps({
        "baseline_version": "0.5.0", "common_assets": [],
        "profiles": {"generic": {"assets": []}},
    }), encoding="utf-8")
    spec = importlib.util.spec_from_file_location("_legacy_baseline", scripts / "baseline.py")
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)

    assert engine.cmd_doctor(argparse.Namespace()) == 0
    assert engine.cmd_reconcile(argparse.Namespace(fix=True, verbose=False)) == 0
    assert engine.state()["openssf_project"] == ""
    snapshot = engine.create_recovery_snapshot(root)
    assert (snapshot / "recovery.json").is_file()
    assert json.loads((snapshot / "baseline/state.json").read_text())["openssf_project"] == ""


@pytest.mark.parametrize("script_root", SCRIPT_ROOTS, ids=["installed", "catalogue"])
def test_real_update_then_repeated_updates_leave_clean_index(script_root, tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    shutil.copytree(REPO_ROOT / ".baseline", source / ".baseline", ignore=ignore)
    shutil.copytree(source / ".baseline", target / ".baseline")
    (target / "scripts").mkdir()
    shutil.copyfile(script_root / "baseline.py", target / "scripts/baseline.py")

    def run(*args):
        result = subprocess.run(
            args, cwd=target, capture_output=True, text=True, timeout=60,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout

    run(sys.executable, "scripts/baseline.py", "bootstrap", "--profile", "ansible",
        "--name", "test-project", "--owner", "test-owner", "--openssf-project", "12345")
    shutil.copytree(script_root / "_project_factory", target / "scripts/_project_factory",
                    dirs_exist_ok=True, ignore=ignore)
    state_path = target / ".baseline/state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["last_reconciled"] = "2000-01-01T00:00:00+00:00"
    override_path = ".github/workflows/ci.yml"
    override = target / override_path
    override.write_text(override.read_text(encoding="utf-8") + "\n# Local override\n",
                        encoding="utf-8")
    original_override = override.read_bytes()
    state["local_overrides"] = [override_path]
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    run("git", "init")
    run("git", "add", ".")

    def commit(message):
        run("git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "-c", "commit.gpgsign=false", "commit", "-m", message)

    commit("initial baseline")
    cache = source / ".baseline/catalog/common/scripts/__pycache__"
    cache.mkdir(exist_ok=True)
    (cache / "generated.pyc").write_bytes(b"generated")

    def update():
        run(sys.executable, "scripts/project_factory.py", "apply-update",
            "--source", str(source))
        assert override.read_bytes() == original_override
        staged = run("git", "diff", "--cached", "--name-only").splitlines()
        assert not any("__pycache__" in path or path.endswith(".pyc") for path in staged)
        return staged

    original_state = state_path.read_bytes()
    assert update() == []
    assert state_path.read_bytes() == original_state

    catalogue = source / ".baseline/catalog/common/CHANGELOG.md"
    catalogue.write_text(catalogue.read_text(encoding="utf-8") + "\nReal update.\n",
                         encoding="utf-8")
    assert ".baseline/catalog/common/CHANGELOG.md" in update()
    assert state_path.read_bytes() != original_state
    commit("apply real same-version update")
    updated_state = state_path.read_bytes()
    for repetition in range(2):
        assert update() == [], repetition
        assert state_path.read_bytes() == updated_state
        assert run("git", "status", "--porcelain") == ""
