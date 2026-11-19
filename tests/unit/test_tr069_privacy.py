import os
from pathlib import Path
import subprocess
import sys


def test_real_ansible_callbacks_do_not_log_the_confidential_value():
    root = Path(__file__).parents[2]
    env = os.environ.copy()
    existing = env.get("ANSIBLE_COLLECTIONS_PATH", os.path.expanduser("~/.ansible/collections"))
    env["ANSIBLE_COLLECTIONS_PATH"] = os.pathsep.join((str(root / ".cache/collections"), existing))
    result = subprocess.run(
        [sys.executable, "-m", "ansible.cli.playbook",
         "tests/integration/tr069.yml", "-i", "localhost,", "-vv"],
        cwd=root, env=env, capture_output=True, text=True, timeout=90, check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "TR069_PRIVACY_SENTINEL" not in output
    assert "requires task-level no_log: true" in output
    assert "censored" in output
