# Changelog

Each release's section becomes the body of its GitHub release. See [RELEASING.md](RELEASING.md).

## v0.1.1 — 2026-10-23

### CLI

- Adapter row: some chargers advertise PDOs but have no contract selected (`UsbHvcHvcIndex` 255). The row now shows `no PD contract · 5 V USB-C fallback` for them. Before, it showed the adapter's rating (e.g. `20.0 V × 5.00 A`) as `negotiated`.
- Adapter row: the `negotiated` volts and amps now come from the active PDO. Adapters without USB-PD show their rating as `… rated`.
- Power row: estimated bus current now divides by the bus voltage, not the adapter rating. On a 5 V fallback, that's e.g. `(~0.70 A @ 20 V)` → `(~2.81 A @ 5 V)`.
- `--json`: the `adapter` object gains `contract` (`[volts, amps]` of the active PDO, or `null`) and `bus_voltage_v`.

### Install / upgrade

- None. Upgrade with `brew upgrade chargestat`, `uv tool upgrade chargestat`, or `pipx upgrade chargestat`.

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
