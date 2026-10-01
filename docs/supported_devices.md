# DrayOS facts support

`drayos_facts` collects read-only `sys version`, `sys iface`, and `show status`
output through the existing `network_cli` connection. It always reports
`changed: false`, including in check mode.

| Model | Firmware | Evidence | Validation scope |
| --- | --- | --- | --- |
| Vigor2927Lac | 4.5.2.2 | Recovered sanitised device-output fixtures | Parser and mocked module tests; live AWX/device execution remains unverified |
| Vigor2927Vac | 4.4.0 | Vendor documentation examples | Parser regression coverage only; not live-device validation |

The recovered stash labels the Lac fixtures as live-device captures; this PR
preserves that provenance but does not independently establish how they were
captured. Fixture parsing does not prove SSH transport, prompt handling, or
pagination works against the router. In particular, parsing the saved
`--- MORE ---` markers does not implement interactive page advancement.
Do not infer support for other models or firmware from these fixtures.

## AWX fixture validation

Use `tests/awx/validate_vigor2927lac.yml` in an AWX project pinned to the PR
revision, with a localhost inventory and no device credentials. The execution
environment needs Python with `venv` support and access to the Python package
index. The job creates a temporary collection layout and virtual environment,
runs the targeted tests, and removes its temporary directory even on failure.
Record the AWX job ID and `scm_revision` with the result. This job tests fixtures
and mocked module execution; it does not contact or validate a live router.
