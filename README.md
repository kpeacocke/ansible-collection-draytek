# ansible-collection-draytek

TODO: describe this project.

This repository is governed by engineering baseline **0.2.0** using the **ansible** profile.

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

## Repository-specific documentation

The collection's engineering specification is the source of truth for scope, architecture and
milestones: [docs/architecture/engineering-specification.md](docs/architecture/engineering-specification.md).

Vendor-derived device evidence is indexed in
[docs/command-reference/CATALOGUES.md](docs/command-reference/CATALOGUES.md). These catalogues
inform future implementation; they do not by themselves establish runtime device support.

Add further setup, operation and usage documentation under `docs/` as the project takes shape.
