import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml


ROOT = Path(__file__).parents[2]
FAKE_COMMAND = """
import json
from pathlib import Path
from ansible.module_utils.basic import AnsibleModule

module = AnsibleModule(argument_spec={
    'state_path': {'type': 'path', 'required': True},
    'commands': {'type': 'list', 'elements': 'raw', 'required': True},
    'retries': {'type': 'int'},
})
path = Path(module.params['state_path'])
data = json.loads(path.read_text())
command = module.params['commands'][0]
if isinstance(command, dict):
    marker = 'V' if data['mode'] == 'enabled' else 'X'
    output = '[' + marker + '] LAN7 '
    module.exit_json(stdout=[output], stdout_lines=[[output]])
data['writes'].append(command)
if command.endswith('192.0.2.54'):
    data['dns']['LAN7']['secondary'] = (
        '192.0.2.55' if data['mode'] == 'unexpected' else '192.0.2.54'
    )
    if data['mode'] == 'other_changed':
        data['dns']['LAN6']['primary'] = '192.0.2.56'
else:
    if data['mode'] != 'clear_failure':
        data['dns']['LAN7']['secondary'] = None
path.write_text(json.dumps(data))
if data['mode'] == 'failure_after_set' and command.endswith('192.0.2.54'):
    module.fail_json(msg='simulated write failure', changed=True)
if data['mode'] == 'clear_failure' and command.endswith('0.0.0.0'):
    module.fail_json(msg='simulated cleanup failure', changed=True)
module.exit_json(stdout=['OK'], stdout_lines=[['OK']])
"""
FAKE_DNS = """
import json
from pathlib import Path
from ansible.module_utils.basic import AnsibleModule

module = AnsibleModule(argument_spec={
    'state_path': {'type': 'path', 'required': True},
    'state': {'type': 'str', 'default': 'gathered'},
    'lan': {'type': 'str'},
    'secondary_server': {'type': 'str'},
})
path = Path(module.params['state_path'])
data = json.loads(path.read_text())
if module.params['state'] == 'merged':
    before = data['dns']['LAN7']['secondary']
    address = module.params['secondary_server']
    desired = None if address == '0.0.0.0' else address
    if before != desired:
        command = 'srv dhcp dns2 lan7 ' + address
        data['writes'].append(command)
        if address == '192.0.2.54':
            data['dns']['LAN7']['secondary'] = (
                '192.0.2.55' if data['mode'] == 'unexpected' else desired
            )
            if data['mode'] == 'other_changed':
                data['dns']['LAN6']['primary'] = '192.0.2.56'
        elif data['mode'] not in ('clear_failure', 'module_clear_failure'):
            data['dns']['LAN7']['secondary'] = None
        path.write_text(json.dumps(data))
        if data['mode'] == 'failure_after_set' and address == '192.0.2.54':
            module.fail_json(msg='simulated write failure', changed=True)
        if data['mode'] in ('clear_failure', 'module_clear_failure') and address == '0.0.0.0':
            module.fail_json(msg='simulated cleanup failure', changed=True)
    module.exit_json(changed=before != desired, before=before, after=desired)
if data['mode'] == 'prewrite_changed' and not data['writes']:
    data['dns']['LAN7']['secondary'] = '192.0.2.55'
    path.write_text(json.dumps(data))
module.exit_json(gathered=data['dns'])
"""


def run_playbook(tmp_path, playbook, *, inventory="localhost,", library=None):
    source = tmp_path / "qualification.yml"
    source.write_text(yaml.safe_dump([playbook]), encoding="utf-8")
    env = {**os.environ, "ANSIBLE_CONFIG": str(ROOT / "ansible.cfg")}
    if library:
        env["ANSIBLE_LIBRARY"] = str(library)
    return subprocess.run(
        [sys.executable, "-m", "ansible.cli.playbook", "-i", inventory, str(source)],
        env=env, text=True, capture_output=True, timeout=60, check=False,
    )


@pytest.mark.parametrize(
    ("mode", "success", "expected_writes", "secondary", "other"),
    [
        ("success", True, 2, None, None),
        ("failure_after_set", False, 2, None, None),
        ("unexpected", False, 1, "192.0.2.55", None),
        ("other_changed", False, 2, None, "192.0.2.56"),
        ("clear_failure", False, 2, "192.0.2.54", None),
        ("module_clear_failure", False, 2, None, None),
        ("prewrite_changed", False, 0, "192.0.2.55", None),
        ("enabled", False, 0, None, None),
    ],
)
@pytest.mark.parametrize("cycle", ["secondary_cycle", "secondary_module_cycle"])
def test_secondary_dns_cycle_restores_or_reports_failure(
    tmp_path, mode, success, expected_writes, secondary, other, cycle,
):
    baseline = {f"LAN{i}": {"primary": None, "secondary": None} for i in range(1, 9)}
    state = tmp_path / "device.json"
    state.write_text(json.dumps({"dns": baseline, "mode": mode, "writes": []}), encoding="utf-8")
    library = tmp_path / "library"
    library.mkdir()
    (library / "fake_command.py").write_text(FAKE_COMMAND, encoding="utf-8")
    (library / "fake_dns.py").write_text(FAKE_DNS, encoding="utf-8")

    playbook = yaml.safe_load(
        (ROOT / "tests/awx/qualify_vigor2927lac_lan7_dns.yml").read_text(encoding="utf-8")
    )[0]
    block = next(task for task in playbook["tasks"] if task["name"].startswith("Qualify secondary DNS"))

    def replace_modules(tasks):
        for task in tasks:
            if "no_log" in task:
                task["no_log"] = False
            for section in ("block", "rescue", "always"):
                if section in task:
                    replace_modules(task[section])
            for original, fake in (
                ("kpeacocke.draytek.drayos_command", "fake_command"),
                ("kpeacocke.draytek.drayos_dns", "fake_dns"),
            ):
                if original in task:
                    task[fake] = {**(task.pop(original) or {}), "state_path": str(state)}

    replace_modules([block])
    result = run_playbook(tmp_path, {
        "hosts": "localhost", "connection": "local", "gather_facts": False,
        "vars": {
            "ansible_python_interpreter": sys.executable,
            "dns_lan7_mode": cycle,
            "dns_baseline": {"gathered": baseline},
        },
        "tasks": [block],
    }, library=library)
    if mode == "module_clear_failure" and cycle == "secondary_cycle":
        success = True
    if mode in ("clear_failure", "module_clear_failure") and cycle == "secondary_module_cycle":
        expected_writes += 1
    assert result.returncode == (0 if success else 2), result.stdout + result.stderr
    data = json.loads(state.read_text(encoding="utf-8"))
    assert data["writes"] == (
        ["srv dhcp dns2 lan7 192.0.2.54"] + ["srv dhcp dns2 lan7 0.0.0.0"] * (expected_writes - 1)
        if expected_writes else []
    )
    assert data["dns"]["LAN7"]["secondary"] == secondary
    assert data["dns"]["LAN6"]["primary"] == other


@pytest.mark.parametrize(
    ("mode", "missing"),
    [
        ("secondary_cycle", "dns_lan7_secondary_cycle_approved"),
        ("secondary_cycle", "dns_lan7_independent_recovery_ready"),
        ("secondary_module_cycle", "dns_lan7_secondary_module_cycle_approved"),
        ("secondary_module_cycle", "dns_lan7_independent_recovery_ready"),
    ],
)
def test_secondary_cycle_requires_approval_and_recovery_before_device_access(tmp_path, mode, missing):
    playbook = yaml.safe_load(
        (ROOT / "tests/awx/qualify_vigor2927lac_lan7_dns.yml").read_text(encoding="utf-8")
    )[0]
    playbook.pop("vars_files")
    playbook["connection"] = "local"
    playbook["pre_tasks"] = playbook["pre_tasks"][:1]
    playbook["tasks"] = [{"ansible.builtin.debug": {"msg": "DEVICE_ACCESS_SENTINEL"}}]
    playbook["vars"] = {
        "dns_lan7_mode": mode,
        "dns_lan7_secondary_cycle_approved": True,
        "dns_lan7_secondary_module_cycle_approved": True,
        "dns_lan7_independent_recovery_ready": True,
    }
    playbook["vars"].pop(missing)
    result = run_playbook(tmp_path, playbook, inventory="HomeOne,")
    assert result.returncode == 2, result.stdout + result.stderr
    assert missing in result.stdout
    assert "DEVICE_ACCESS_SENTINEL" not in result.stdout
