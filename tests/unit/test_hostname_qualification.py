import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml


ROOT = Path(__file__).parents[2]
FAKE_MODULE = """
import json
from pathlib import Path
from ansible.module_utils.basic import AnsibleModule

module = AnsibleModule(argument_spec={
    'state_path': {'type': 'path', 'required': True},
    'state': {'type': 'str', 'default': 'merged'},
    'config': {'type': 'dict'},
    'source': {'type': 'str', 'default': 'ssh'},
}, supports_check_mode=True)
path = Path(module.params['state_path'])
data = json.loads(path.read_text())
before = {'hostname': data['hostname']}
if module.params['state'] == 'gathered':
    module.exit_json(changed=False, gathered=before)
desired = module.params['config']
if data.get('reject_original') and desired['hostname'] == 'original-router':
    module.fail_json(msg='Original name cannot be restored by this module', changed=False)
changed = before != desired
if changed and not module.check_mode:
    if data.get('fail_restore') and desired['hostname'] == 'original-router':
        module.fail_json(msg='Injected restoration failure', changed=False)
    data['hostname'] = desired['hostname']
    data['writes'].append(module.params['source'] + ':' + desired['hostname'])
    if data.pop('fail_after_apply', False):
        path.write_text(json.dumps(data))
        module.fail_json(msg='Injected lost acknowledgement', changed=True)
    path.write_text(json.dumps(data))
commands = ['sys name ' + desired['hostname']] if changed else []
module.exit_json(changed=changed, before=before, after=desired, commands=commands,
                 diff={'before': before, 'after': desired})
"""


@pytest.mark.parametrize("recovery,simulate_https,failure,success,expected_writes", [
    (False, False, "", True, ["ssh:HomeOne-test", "ssh:original-router"]),
    (True, True, "", True, ["ssh:HomeOne-test", "https:original-router"]),
    (True, False, "", False, ["ssh:HomeOne-test", "ssh:original-router"]),
    (False, False, "fail_after_apply", False, ["ssh:HomeOne-test", "ssh:original-router"]),
    (False, False, "reject_original", False, []),
    (False, False, "fail_restore", False, ["ssh:HomeOne-test"]),
])
def test_real_qualification_tasks_restore_or_fail_explicitly(
    tmp_path, recovery, simulate_https, failure, success, expected_writes,
):
    state = tmp_path / "device.json"
    state.write_text(json.dumps({
        "hostname": "original-router", "writes": [], **({failure: True} if failure else {}),
    }))
    library = tmp_path / "library"
    library.mkdir()
    (library / "fake_hostname.py").write_text(FAKE_MODULE)
    tasks = yaml.safe_load((ROOT / "tests/awx/tasks/qualify_hostname.yml").read_text())

    def substitute_transport(items):
        for task in items:
            for section in ("block", "rescue", "always"):
                if section in task:
                    substitute_transport(task[section])
            if "kpeacocke.draytek.drayos_hostname" in task:
                task["fake_hostname"] = {
                    **task.pop("kpeacocke.draytek.drayos_hostname"),
                    "state_path": str(state),
                }
            if "ansible.builtin.pause" in task:
                task.pop("ansible.builtin.pause")
                if simulate_https:
                    task["fake_hostname"] = {
                        "state_path": str(state), "source": "https",
                        "config": {"hostname": "original-router"},
                    }
                else:
                    task["ansible.builtin.debug"] = {"msg": "No independent restoration"}

    substitute_transport(tasks)
    playbook = tmp_path / "qualify.yml"
    playbook.write_text(yaml.safe_dump([{
        "hosts": "localhost", "connection": "local", "gather_facts": False,
        "vars": {
            "ansible_python_interpreter": sys.executable,
            "drayos_hostname_test_name": "HomeOne-test",
            "drayos_hostname_validation_backend": "paramiko",
            "drayos_hostname_recovery_rehearsal": recovery,
        },
        "tasks": tasks,
    }]))
    result = subprocess.run(
        [sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(playbook)],
        env={**os.environ, "ANSIBLE_LIBRARY": str(library),
             "ANSIBLE_CONFIG": str(ROOT / "ansible.cfg")},
        text=True, capture_output=True, timeout=60, check=False,
    )
    assert result.returncode == (0 if success else 2), result.stdout + result.stderr
    final = json.loads(state.read_text())
    assert final["writes"] == expected_writes
    assert final["hostname"] == ("HomeOne-test" if failure == "fail_restore" else "original-router")
    assert ("Hostname qualification passed via" in result.stdout) is success


@pytest.mark.parametrize("missing", [
    "drayos_hostname_change_approved", "drayos_hostname_recovery_ready",
    "drayos_hostname_test_name", "drayos_hostname_validation_backend",
])
def test_missing_qualification_approval_fails_before_preparation(tmp_path, missing):
    source = yaml.safe_load((ROOT / "tests/awx/qualify_vigor2927lac_hostname.yml").read_text())[0]
    source.pop("vars_files")
    source["hosts"] = "localhost"
    source["connection"] = "local"
    source.pop("vars")
    source["pre_tasks"] = source["pre_tasks"][:1]
    source["tasks"] = [{"ansible.builtin.debug": {"msg": "DEVICE_ACCESS_SENTINEL"}}]
    approvals = {
        "drayos_hostname_change_approved": True,
        "drayos_hostname_recovery_ready": True,
        "drayos_hostname_test_name": "HomeOne-test",
        "drayos_hostname_validation_backend": "paramiko",
    }
    approvals.pop(missing)
    playbook = tmp_path / "approval.yml"
    playbook.write_text(yaml.safe_dump([source]))
    result = subprocess.run(
        [sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,",
         str(playbook), "-e", json.dumps(approvals)],
        env={**os.environ, "ANSIBLE_CONFIG": str(ROOT / "ansible.cfg")},
        text=True, capture_output=True, timeout=30, check=False,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "DEVICE_ACCESS_SENTINEL" not in result.stdout
    assert "Approve the exact temporary name" in result.stdout
