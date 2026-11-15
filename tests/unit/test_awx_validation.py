import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml


REPO_ROOT = Path(__file__).parents[2]


@pytest.mark.parametrize("key_state", ["missing", "verified", "wrong-host"])
def test_live_validation_prepares_only_a_verified_host_key(tmp_path, key_state):
    source = yaml.safe_load(
        (REPO_ROOT / "tests/awx/validate_vigor2927lac_live.yml").read_text()
    )
    preparation = source[0]
    preparation["tasks"] = preparation["tasks"][:3]
    playbook = tmp_path / "prepare.yml"
    playbook.write_text(yaml.safe_dump([preparation]))
    inventory = tmp_path / "inventory.json"
    inventory.write_text(json.dumps({
        "all": {"hosts": {
            "HomeOne": {"ansible_host": "192.0.2.1"},
            "localhost": {
                "ansible_connection": "local",
                "ansible_python_interpreter": sys.executable,
            },
        }},
    }))
    extra_vars = {}
    if key_state != "missing":
        key_path = tmp_path / "test-key"
        subprocess.run(
            ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key_path)],
            check=True, capture_output=True,
        )
        public_key = key_path.with_suffix(".pub").read_text().split()
        host = "192.0.2.1" if key_state == "verified" else "192.0.2.2"
        extra_vars["drayos_validation_known_host"] = f"{host} {' '.join(public_key[:2])}"
    home = tmp_path / "home"
    home.mkdir()
    result = subprocess.run(
        [
            sys.executable, "-m", "ansible.cli.playbook",
            "-i", str(inventory), str(playbook), "-e", json.dumps(extra_vars),
        ],
        env={
            **os.environ,
            "HOME": str(home),
            "ANSIBLE_CONFIG": str(REPO_ROOT / "ansible.cfg"),
            "PYTHONPATH": os.pathsep.join(sys.path),
        },
        text=True, capture_output=True, check=False,
    )
    known_hosts = home / ".ssh/known_hosts"
    if key_state == "verified":
        assert result.returncode == 0, result.stdout + result.stderr
        lookup = subprocess.run(
            ["ssh-keygen", "-F", "192.0.2.1", "-f", str(known_hosts)],
            text=True, capture_output=True, check=False,
        )
        assert lookup.returncode == 0, lookup.stderr
        assert public_key[1] in lookup.stdout
        assert "192.0.2.1" not in known_hosts.read_text()
    else:
        assert result.returncode == 2, result.stdout + result.stderr
        assert "FAILED" in result.stdout
        assert not known_hosts.exists() or not known_hosts.read_text().strip()
