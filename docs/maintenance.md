# Maintenance operations

Owner: the repository owner (`@kpeacocke`, per `.github/CODEOWNERS`) owns
triage, releases, baseline updates, and security response.

## Issue and regression triage

- Bug reports need the collection version, ansible-core version, device
  model/firmware, and sanitised output (see
  [troubleshooting](troubleshooting.md)).
- A reproducible defect gets a failing regression test before its fix;
  fixes merge through pull requests with the full CI gate.
- Unknown device behaviour blocks the affected feature rather than being
  guessed around; record exactly what evidence is missing.
- Suspected vulnerabilities follow the [security policy](../SECURITY.md),
  not public issues.

## Supported-version policy

- Supported runtime and device combinations are exactly those in the
  [qualification matrix](qualification-matrix.md).
- Dropping or adding an ansible-core/Python/netcommon combination changes
  the CI matrix and the matrix document in the same pull request.
- Device support changes only with fixtures and recorded validation per the
  [fixture contribution procedure](../CONTRIBUTING.md#contributing-drayos-device-fixtures).

## Recurring qualification

Requalification is required after:

- a dependency floor change (`ansible-core`, `ansible.netcommon`) — rerun
  the full unit matrix and sanity;
- a device firmware change on a validated device — rerun the read-only live
  validation playbook and record the new job ID, revision, and firmware in
  the [device matrix](supported_devices.md) before claiming the new
  firmware;
- any change to transport, platform, or write-guard code — live claims from
  before the change do not carry forward automatically.

## Engineering baseline

The repository baseline (`.baseline/`, `scripts/baseline.py`) is owned
upstream in `kpeacocke/engineering-baseline-template`. Scheduled
`baseline-update` runs open update pull requests; defects in managed files
are fixed upstream first, not patched locally, and deliberate divergences
are registered as local overrides in `.baseline/state.json`. Conformance is
enforced by the `baseline` CI check.

## Releases

Releases follow the [Release A criteria](release-a.md) and its successors:
changelog generated from `changelogs/fragments/`, the verified revision
tagged, the built artefact inspected and hardware-qualified before
publication, and release notes disclosing limitations.
