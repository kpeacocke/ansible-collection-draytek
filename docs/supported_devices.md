# Supported devices

This collection's DrayOS support is built from real captured device output
(the [engineering specification's discovery rule](architecture/engineering-specification.md#65-discovery-before-implementation)). DrayTek publishes a Command
Reference per product on its regional Downloads pages, and the CLI is
self-documenting (`?` lists commands), but this collection's normalised
representation must still be validated against real command output before a
parser is written, and coverage grows through fixtures contributed by device
owners; see
[CONTRIBUTING.md](../CONTRIBUTING.md#contributing-drayos-device-fixtures).

These terms are not interchangeable:

- **Supported** — the collection is designed to work with this platform family.
- **Tested** — a sanitised real-device fixture exists for this exact
  product/firmware combination, with hardware verification recorded
  separately where available.
- **Expected compatible** — believed to work by architectural similarity to a
  tested product, but not itself verified.
- **Evidence only** — vendor documentation has been catalogued, but no
  collection transport or runtime support has been established.

Never infer that an entire Vigor family works because one model passed tests.

## Validated DrayOS facts

`drayos_facts` collects read-only `sys version`, `sys iface`, and `show status`
output through the existing `network_cli` connection. It always reports
`changed: false`, including in check mode.

| Model | Firmware | Evidence | Validation scope |
| --- | --- | --- | --- |
| Vigor2927Lac | 4.5.2.2 | Recovered sanitised device-output fixtures | Parser/module/transport regressions and read-only live AWX validation (job #970) |
| Vigor2927Vac | 4.4.0 | Vendor documentation examples | Parser regression coverage only; not live-device validation |

The recovered stash labels the Lac fixtures as live-device captures; this PR
preserves that provenance but does not independently establish how they were
captured. Fixture parsing does not prove SSH transport, prompt handling, or
pagination works against the router. The transport now answers the captured `--- MORE ---` prompt with Space,
without a carriage return, for `sys iface` and `show status`. Repeated prompts
are handled up to 64 advances per command; the persistent command timeout
bounds stalled or over-limit output. Tests exercise the actual netcommon
Paramiko and libssh receive loops with gated multi-page responses.
Live AWX job [#970](https://awx.ambitiouscake.com/jobs/playbook/970/output)
validated revision `04313ae`: all facts completed, hostname was populated,
interface 11 and WAN 6 were present, and the router reported `changed=false`.
The live command prompt ends with two spaces after `>`; terminal matching
accepts trailing horizontal whitespace, with receive-loop regression coverage.
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
facts. A playbook-adjacent collection layout links directly to the project plugins
so validation executes the checked-out revision even on workers whose
configured collection paths do not match their execution directory.
It changes no router configuration.

## Additional evidence-only families

| Product | Platform | Firmware | Tested | CI Tested | Support Level | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| VigorAP 1060C | Web UI management evidence | V1.4.9 | No | No | Evidence only | Catalogue records Web UI evidence; no CLI, HTTP or API transport is documented. |
| VigorAP 918R | Web UI management evidence | V1.4.6 | No | No | Evidence only | Catalogue records management evidence; no CLI, HTTP or API transport is documented. |
| VigorSwitch P2100/G2100 | Telnet/console CLI evidence | V2.8.3 | No | No | Evidence only | CLI catalogue exists; SSH parity, readback, idempotency and runtime support are unverified. |
| VigorSwitch G1080 | Web UI management evidence | V1.04.04 | No | No | Evidence only | Catalogue records Web UI evidence; no CLI, HTTP or API transport is documented. |
