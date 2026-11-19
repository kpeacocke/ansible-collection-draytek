import json
from pathlib import Path
import subprocess
import sys
import tarfile


REPO_ROOT = Path(__file__).parents[2]


def test_built_collection_contains_runtime_and_not_repository_tooling(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "ansible.cli.galaxy", "collection", "build",
         "--output-path", str(tmp_path)],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    archives = list(tmp_path.glob("*.tar.gz"))
    assert len(archives) == 1
    with tarfile.open(archives[0], "r:gz") as archive:
        names = {member.name.rstrip("/") for member in archive.getmembers()}
        manifest_file = archive.extractfile("MANIFEST.json")
        assert manifest_file is not None
        manifest = json.load(manifest_file)
    forbidden = {
        ".github", ".baseline", "scripts", "config", "AGENTS.md",
        ".devcontainer", ".vscode", ".cache", ".venv",
        "tests/unit/test_project_factory.py",
        "tests/unit/test_ci_workflows.py",
        "tests/unit/test_collection_build.py",
    }
    assert not {
        name for name in names
        if any(name == path or name.startswith(path + "/") for path in forbidden)
    }
    assert {
        "plugins/modules/drayos_command.py",
        "plugins/modules/drayos_facts.py",
        "plugins/modules/drayos_hostname.py",
        "plugins/modules/drayos_ntp.py",
        "plugins/modules/drayos_tr069.py",
        "plugins/modules/drayos_dns.py",
        "plugins/module_utils/network/drayos/tr069.py",
        "plugins/terminal/drayos.py",
        "plugins/cliconf/drayos.py",
        "plugins/module_utils/network/drayos/connection.py",
        "meta/runtime.yml", "README.md", "docs/testing.md",
        "tests/integration/hostname.yml",
        "tests/integration/targets/drayos_hostname/tasks/main.yml",
        "tests/integration/ntp.yml",
        "tests/integration/targets/drayos_ntp/tasks/main.yml",
        "tests/integration/tr069.yml",
        "tests/integration/targets/drayos_tr069/tasks/main.yml",
        "tests/integration/dns.yml",
    } <= names
    info = manifest["collection_info"]
    assert info["repository"] == "https://github.com/kpeacocke/ansible-collection-draytek"
    assert info["issues"] == "https://github.com/kpeacocke/ansible-collection-draytek/issues"
