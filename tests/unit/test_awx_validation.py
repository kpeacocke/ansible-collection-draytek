import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml


REPO_ROOT = Path(__file__).parents[2]


@pytest.mark.parametrize("playbook_name", [
    "validate_vigor2927lac_live.yml", "qualify_vigor2927lac_hostname.yml",
])
@pytest.mark.parametrize(
    "key_state,limit,extra_policy,environment,inventory_policy,success",
    [
        ("verified", "", {}, {}, {}, True),
        ("verified", "HomeOne", {}, {}, {}, True),
        ("missing", "", {}, {}, {}, False),
        ("missing", "HomeOne", {}, {}, {}, False),
        ("wrong-host", "HomeOne", {}, {}, {}, False),
        ("verified", "HomeOne", {}, {"ANSIBLE_HOST_KEY_AUTO_ADD": "True"}, {}, False),
        ("verified", "HomeOne", {"ansible_host_key_checking": False}, {}, {}, False),
        ("verified", "HomeOne", {"ansible_libssh_host_key_checking": False}, {}, {}, False),
        ("verified", "HomeOne", {"ansible_libssh_host_key_auto_add": True}, {}, {}, False),
        ("verified", "HomeOne", {}, {}, {"ansible_libssh_host_key_checking": False}, True),
    ],
)
def test_live_validation_cannot_bypass_host_key_preparation(
    tmp_path, key_state, limit, extra_policy, environment, inventory_policy, success, playbook_name,
):
    source = yaml.safe_load(
        (REPO_ROOT / "tests/awx" / playbook_name).read_text()
    )
    for play in source:
        play["vars"] = {
            **yaml.safe_load((REPO_ROOT / "tests/awx/vars/live_validation.yml").read_text()),
            **play.get("vars", {}),
        }
        play.pop("vars_files")
        expanded = []
        for task in play["pre_tasks"]:
            if "ansible.builtin.import_tasks" in task:
                expanded.extend(yaml.safe_load(
                    (REPO_ROOT / "tests/awx" / task["ansible.builtin.import_tasks"]).read_text()
                ))
            else:
                expanded.append(task)
        play["pre_tasks"] = expanded
        for task in [*play.get("pre_tasks", []), *play.get("tasks", [])]:
            if "ansible.builtin.include_tasks" in task:
                task.clear()
                task.update(
                    name="Device phase reached",
                    vars={"ansible_connection": "local"},
                    **{"ansible.builtin.debug": {"msg": "TEST_DEVICE_PHASE"}},
                )
            if "ansible.builtin.command" in task:
                task.pop("ansible.builtin.command")
                task["ansible.builtin.debug"] = {"msg": "Dependency installation stub"}
    project = tmp_path / "project"
    playbook = project / "tests/awx/validate.yml"
    playbook.parent.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / "ansible.cfg", project / "ansible.cfg")
    playbook.write_text(yaml.safe_dump(source))
    inventory = tmp_path / "inventory.json"
    inventory.write_text(json.dumps({
        "all": {"hosts": {
            "HomeOne": {"ansible_host": "192.0.2.1", **inventory_policy},
            "localhost": {"ansible_connection": "local"},
        }},
    }))
    extra_vars = {
        "drayos_hostname_change_approved": True,
        "drayos_hostname_recovery_ready": True,
        "drayos_hostname_test_name": "HomeOne-test",
        "drayos_hostname_validation_backend": "paramiko",
        **extra_policy,
    }
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
            *(["--limit", limit] if limit else []),
        ],
        env={
            **os.environ,
            "HOME": str(home),
            "ANSIBLE_CONFIG": str(project / "ansible.cfg"),
            "ANSIBLE_HOST_KEY_CHECKING": "False",
            "PYTHONPATH": os.pathsep.join(sys.path),
            **environment,
        },
        text=True, capture_output=True, check=False,
    )
    known_hosts = home / ".ssh/known_hosts"
    if success:
        assert result.returncode == 0, result.stdout + result.stderr
        assert "TEST_DEVICE_PHASE" in result.stdout
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
        assert "TEST_DEVICE_PHASE" not in result.stdout
        assert not known_hosts.exists() or not known_hosts.read_text().strip()
