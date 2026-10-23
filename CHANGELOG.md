# Changelog

Each release's section becomes the body of its GitHub release. See [RELEASING.md](RELEASING.md).

## v0.1.0 — 2026-10-23

First release.

### CLI

- `chargestat` prints one snapshot: adapter contract, advertised PDOs, charge status, rate, time to full/empty, power flow, battery capacity, health, and gauge age.
- `-w [SEC]` refreshes in place every SEC seconds (default 2). `-n N` stops after N refreshes.
- `--json` prints machine-readable output: one object, or one object per line with `-w`.
- `-H [HOURS]` plots charge % and battery power over the last HOURS hours (default 24) from the system powerlog. With `--json`, it prints the samples as an array.
- Time to empty uses the 15-minute mean discharge current from the powerlog, with the macOS estimate alongside.
- Exits with status 2 on a Mac without a battery.

### Install / upgrade

- New: `brew install tjdcs/tap/chargestat`, `uv tool install chargestat`, or `uvx chargestat`.
- Requires macOS and Python ≥ 3.10. No runtime dependencies.
