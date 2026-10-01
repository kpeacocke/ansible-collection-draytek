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
pagination works against the router. The transport now answers the captured `--- MORE ---` prompt with Space,
without a carriage return, for `sys iface` and `show status`. Repeated prompts
are handled up to 64 advances per command; the persistent command timeout
bounds stalled or over-limit output. Tests exercise the actual netcommon
Paramiko and libssh receive loops with gated multi-page responses.
Do not infer support for other models or firmware from these fixtures.

## AWX fixture validation

Use `tests/awx/validate_vigor2927lac.yml` in an AWX project pinned to the PR
revision, with a localhost inventory and no device credentials. The execution
environment needs Python with `venv` support and access to the Python package
index. The job creates a temporary collection layout and virtual environment,
runs the targeted tests, and removes its temporary directory even on failure.
Record the AWX job ID and `scm_revision` with the result. This job tests fixtures
and mocked module execution; it does not contact or validate a live router.


`tests/awx/validate_vigor2927lac_live.yml` uses the existing `HomeOne` inventory
host and its AWX SSH credential for a read-only check. It asserts model,
firmware, nonempty hostname, interface 11 and WAN 6, without logging device
facts. It must run without a host limit so localhost collection setup executes.
It changes no router configuration.
