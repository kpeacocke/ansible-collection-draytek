import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml
from ansible import constants as C


ROOT = Path(__file__).parents[2]
FAKE_MODULE = """
import json
from pathlib import Path
from ansible.module_utils.basic import AnsibleModule

module = AnsibleModule(argument_spec={
    'state_path': {'type': 'path', 'required': True},
    'commands': {'type': 'list', 'elements': 'str', 'required': True},
})
path = Path(module.params['state_path'])
data = json.loads(path.read_text())
command = module.params['commands'][0]
if command == 'sys time show':
    output = (
        '  Primary NTP Server: [' + data['primary'] + ']\\n'
        '  Secondary NTP Server: [' + data['secondary'] + ']\\n'
    )
    if data.get('duplicate') or (data['mode'] == 'duplicate_after_apply' and data['writes']):
        output += '  Primary NTP Server: [duplicate.example]\\n'
    module.exit_json(changed=False, stdout=[output], stdout_lines=[output.splitlines()])
data['writes'].append(command)
if data['mode'] == 'restore_failure' and command.endswith('original.example'):
    path.write_text(json.dumps(data))
    module.fail_json(msg='Command execution failed (CommandError); device output suppressed', changed=True)
if data['mode'] != 'no_change':
    key = 'secondary' if data['mode'] == 'secondary' else 'primary'
    data[key] = command.split()[-1]
path.write_text(json.dumps(data))
if data['mode'] == 'failure_after_apply' and command.endswith('time.cloudflare.com'):
    module.fail_json(msg='Command execution failed (CommandError); device output suppressed', changed=True)
module.exit_json(changed=False, stdout=['OK'], stdout_lines=[['OK']])
"""


def run_playbook(tmp_path, playbook, library=None, check=False):
    source = tmp_path / "qualification.yml"
    source.write_text(yaml.safe_dump([playbook]), encoding="utf-8")
    env = {
        **os.environ,
        "ANSIBLE_CONFIG": str(ROOT / "ansible.cfg"),
        "ANSIBLE_COLLECTIONS_PATH": os.pathsep.join([str(ROOT / ".cache/collections"), *C.COLLECTIONS_PATHS]),
    }
    if library:
        env["ANSIBLE_LIBRARY"] = str(library)
    command = [sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(source)]
    if check:
        command.append("--check")
    return subprocess.run(
        command,
        env=env, text=True, capture_output=True, timeout=60, check=False,
    )


@pytest.mark.parametrize(
    ("mode", "success", "expected_writes", "primary", "secondary"),
    [
        ("primary", True, 2, "original.example", ""),
        ("failure_after_apply", False, 2, "original.example", ""),
        ("secondary", False, 1, "original.example", "time.cloudflare.com"),
        ("restore_failure", False, 2, "time.cloudflare.com", ""),
        ("no_change", False, 1, "original.example", ""),
        ("duplicate", False, 0, "original.example", ""),
        ("duplicate_after_apply", False, 1, "time.cloudflare.com", ""),
    ],
)
def test_qualification_restores_or_reports_manual_recovery(
    tmp_path, mode, success, expected_writes, primary, secondary,
):
    state = tmp_path / "device.json"
    state.write_text(json.dumps({
        "primary": "original.example", "secondary": "", "writes": [], "mode": mode,
        "duplicate": mode == "duplicate",
    }), encoding="utf-8")
    library = tmp_path / "library"
    library.mkdir()
    (library / "fake_command.py").write_text(FAKE_MODULE, encoding="utf-8")
    tasks = yaml.safe_load(
        (ROOT / "tests/awx/tasks/qualify_ntp_server.yml").read_text(encoding="utf-8")
    )

    def replace_commands(items):
        for task in items:
            for section in ("block", "rescue", "always"):
                if section in task:
                    replace_commands(task[section])
            if "kpeacocke.draytek.drayos_command" in task:
                task["fake_command"] = {
                    **task.pop("kpeacocke.draytek.drayos_command"),
                    "state_path": str(state),
                }

    replace_commands(tasks)
    result = run_playbook(tmp_path, {
        "hosts": "localhost", "connection": "local", "gather_facts": False,
        "vars": {"ansible_python_interpreter": sys.executable}, "tasks": tasks,
    }, library)
    assert result.returncode == (0 if success else 2), result.stdout + result.stderr
    data = json.loads(state.read_text(encoding="utf-8"))
    assert len(data["writes"]) == expected_writes
    assert (data["primary"], data["secondary"]) == (primary, secondary)
    assert "SECRET_DEVICE_OUTPUT" not in result.stdout + result.stderr
    if mode in ("secondary", "restore_failure", "duplicate_after_apply"):
        assert "restore the original settings through HTTPS" in result.stdout


@pytest.mark.parametrize(
    ("missing", "check"),
    [("drayos_ntp_test_approved", False), ("drayos_ntp_recovery_ready", False), (None, True)],
)
def test_missing_approval_or_check_mode_stops_before_device_access(tmp_path, missing, check):
    playbook = yaml.safe_load(
        (ROOT / "tests/awx/qualify_vigor2927lac_ntp.yml").read_text(encoding="utf-8")
    )[0]
    playbook.pop("vars_files")
    playbook["hosts"] = "localhost"
    playbook["connection"] = "local"
    playbook["pre_tasks"] = playbook["pre_tasks"][:1]
    playbook["tasks"] = [{"ansible.builtin.debug": {"msg": "DEVICE_ACCESS_SENTINEL"}}]
    playbook["vars"] = {
        "drayos_ntp_test_approved": True,
        "drayos_ntp_recovery_ready": True,
    }
    if missing:
        playbook["vars"].pop(missing)
    result = run_playbook(tmp_path, playbook, check=check)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "DEVICE_ACCESS_SENTINEL" not in result.stdout
    assert "Approve the exact NTP test" in result.stdout


@pytest.mark.parametrize(
    ("host", "port", "backend"),
    [("192.0.2.1", 22, "paramiko"), ("192.168.5.1", 23, "paramiko"),
     ("192.168.5.1", 22, "libssh")],
)
def test_unapproved_target_stops_before_device_access(tmp_path, host, port, backend):
    playbook = yaml.safe_load(
        (ROOT / "tests/awx/qualify_vigor2927lac_ntp.yml").read_text(encoding="utf-8")
    )[0]
    playbook.pop("vars_files")
    playbook["hosts"] = "localhost"
    playbook["connection"] = "local"
    playbook["pre_tasks"] = playbook["pre_tasks"][:2]
    playbook["tasks"] = [{"ansible.builtin.debug": {"msg": "DEVICE_ACCESS_SENTINEL"}}]
    playbook["vars"] = {
        "drayos_ntp_test_approved": True, "drayos_ntp_recovery_ready": True,
        "ansible_host": host, "ansible_port": port, "ansible_network_cli_ssh_type": backend,
    }
    result = run_playbook(tmp_path, playbook)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "DEVICE_ACCESS_SENTINEL" not in result.stdout
