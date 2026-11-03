from pathlib import Path
import os
import subprocess

import pytest
import yaml


WORKFLOW_ROOT = Path(__file__).parents[2] / ".github" / "workflows"
TOKEN_PERMISSIONS = {
    "actions", "artifact-metadata", "attestations", "checks", "contents",
    "deployments", "discussions", "id-token", "issues", "models", "packages",
    "pages", "pull-requests", "security-events", "statuses",
}


def test_workflows_declare_only_supported_token_permissions():
    for path in WORKFLOW_ROOT.glob("*.yml"):
        workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
        scopes = [workflow.get("permissions", {})]
        scopes.extend(job.get("permissions", {}) for job in workflow["jobs"].values())
        for permissions in scopes:
            if isinstance(permissions, dict):
                assert set(permissions) <= TOKEN_PERMISSIONS, path.name


def test_updater_uses_same_workflow_capable_credential_for_git_and_prs():
    workflow = yaml.safe_load(
        (WORKFLOW_ROOT / "baseline-update.yml").read_text(encoding="utf-8")
    )
    steps = workflow["jobs"]["update"]["steps"]
    checkout = steps[0]
    publish = next(step for step in steps if step.get("name") == "Open update pull request when required")
    expected = "${{ secrets.BASELINE_UPDATE_TOKEN || github.token }}"
    assert checkout["with"]["token"] == expected
    assert publish["env"]["GH_TOKEN"] == expected


@pytest.mark.parametrize("pending_changes,expected_status", [(False, 0), (True, 1)])
def test_updater_without_credential_only_succeeds_when_baseline_is_current(pending_changes, expected_status):
    workflow = yaml.safe_load(
        (WORKFLOW_ROOT / "baseline-update.yml").read_text(encoding="utf-8")
    )
    publish = next(
        step for step in workflow["jobs"]["update"]["steps"]
        if step.get("name") == "Open update pull request when required"
    )
    diff_status = 1 if pending_changes else 0
    script = f"git() {{ return {diff_status}; }}\n" + publish["run"]
    environment = os.environ.copy()
    environment["BASELINE_UPDATE_TOKEN"] = ""
    result = subprocess.run(
        ["bash", "-eu", "-c", script], env=environment, text=True,
        capture_output=True, check=False,
    )
    assert result.returncode == expected_status
    if pending_changes:
        assert "::error::Set BASELINE_UPDATE_TOKEN" in result.stdout
    else:
        assert "Baseline is current." in result.stdout
