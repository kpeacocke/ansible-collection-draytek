# Qualification matrix

Support is claimed per verified combination, not per family. Untested
combinations are labelled; metadata minimums are declared floors, not tested
claims.

## Controller runtime combinations

Each row is exercised on every pull request and push to `main` by the CI
`units` matrix (`.github/workflows/ci.yml`); the unit suite includes the real
netcommon Paramiko and libssh receive-loop tests.

| Python | ansible-core | ansible.netcommon | Executable test |
| --- | --- | --- | --- |
| 3.11 | >=2.19,<2.20 | 6.0.0 | CI `units (3.11, >=2.19,<2.20, 6.0.0)` |
| 3.12 | >=2.20,<2.21 | 8.7.1 | CI `units (3.12, >=2.20,<2.21, 8.7.1)` |
| 3.14 | >=2.21,<2.22 | 8.7.1 | CI `units (3.14, >=2.21,<2.22, 8.7.1)` |

`galaxy.yml` declares `ansible.netcommon >= 6.0.0` and `meta/runtime.yml`
declares `requires_ansible >= 2.19.0`; versions inside those floors but
outside the rows above are **untested**. Core versions beyond 2.22 are
untested until a matrix row is added.

## Device, firmware and transport combinations

| Device | Firmware | SSH backend | Status | Evidence |
| --- | --- | --- | --- | --- |
| Vigor2927Lac | 4.5.2.2 | Paramiko | Live qualified (reads; writes within module guards) | [Device matrix](supported_devices.md) AWX job records |
| Vigor2927Lac | 4.5.2.2 | libssh | **Untested live** — unit receive-loop coverage only; the one live launch failed before producing events | [Device matrix](supported_devices.md) |
| Vigor2927Vac | 4.4.0 | n/a | Fixture regression only, from vendor documentation examples — **not live validated** | `tests/fixtures/drayos/vigor2927/4.4.0/` |
| Any other model/firmware | — | — | **Unsupported/untested** | — |

Write qualification is narrower still: each write module's guard encodes the
exact combination its evidence covers (see [ntp](ntp.md) and the DNS section
of the [device matrix](supported_devices.md)). Reboot persistence has not
been qualified for any write.

## Adding a combination

A new combination becomes claimable only with a planned executable test:
a CI matrix row for runtimes, or sanitised fixtures plus recorded read-only
live validation for devices
([contribution rules](../CONTRIBUTING.md#contributing-drayos-device-fixtures)).
