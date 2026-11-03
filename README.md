# ansible-collection-draytek

TODO: describe this project.

This repository is governed by engineering baseline **0.5.1** using the **ansible** profile.

## Normal workflow

Verify the local baseline and GitHub settings:

```powershell
.\baseline.ps1 doctor
```

The source repository is recorded in `.baseline/state.json`; no separate GitHub repository variable is required.

Request an update from the central golden baseline:

```powershell
.\baseline.ps1 update
```

For local-only structural/drift diagnosis:

```powershell
python .\scripts\baseline.py doctor
```

In VS Code, use `/plan`, `/implement`, `/debug`, `/verify`, `/review`, `/preflight`, and `/ship`. Durable methodology lives in `.github/skills/`; repository-specific guidance can extend the managed instructions without replacing it.

## Scheduled baseline updates

Configure the repository Actions secret `BASELINE_UPDATE_TOKEN` before publishing
automated baseline updates. Use a fine-grained personal access token restricted to
this repository with Contents, Pull requests, and Workflows read/write permissions,
or a classic token with `repo` and `workflow` scopes. Do not put the token in Git.
The updater uses this credential for checkout, Git pushes, and PR creation, so
workflow-file updates are authorised and PR CI can run.

`GITHUB_TOKEN` cannot be granted a `workflows` permission. Without
`BASELINE_UPDATE_TOKEN`, a current baseline can still be checked, but publishing
pending changes fails explicitly. For a private baseline source repository,
configure a separate read-only `BASELINE_READ_TOKEN`.

## Repository-specific documentation

The collection's engineering specification is the source of truth for scope, architecture and
milestones: [docs/architecture/engineering-specification.md](docs/architecture/engineering-specification.md).

Vendor-derived device evidence is indexed in
[docs/command-reference/CATALOGUES.md](docs/command-reference/CATALOGUES.md). These catalogues
inform future implementation; they do not by themselves establish runtime device support.

Add further setup, operation and usage documentation under `docs/` as the project takes shape.
