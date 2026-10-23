# chargestat

Mac power adapter, charge rate, and time to full/empty in the terminal. Read-only, no sudo, no dependencies beyond the Python standard library.

<!-- Absolute URL so the GIF also renders on PyPI. Re-record with: vhs docs/demo.tape -->
![chargestat showing a charging snapshot, then a 24-hour charge and battery-power history plot](https://raw.githubusercontent.com/tjdcs/chargestat/main/docs/demo.gif)

```sh
brew install tjdcs/tap/chargestat
```

Or try it without installing: `uvx chargestat`. See [Install](#install) for other options.

```
Adapter  100 W · pd charger · 20.0 V × 5.00 A negotiated
PDOs     5V 3A · 9V 3A · 15V 3A · [20V 5A]
Status   Charging  23% █████░░░░░░░░░░░░░░░
Rate     +476 mA · +9.0 %/h
Time     10h 14m to full (macOS)
Power    ~14.0 W in → 8.8 W system, +5.3 W battery · ~14.9 W at wall
Battery  1169/5312 mAh · 11.44 V · 30.6 °C
Health   85% of design (6249 mAh) · 437 cycles
Updated  9 s ago by battery gauge
```

## Install

Requires macOS. Homebrew provides Python; with uv, any Python ≥ 3.10 works.

| | Homebrew | uv | pipx |
|---|---|---|---|
| Install | `brew install tjdcs/tap/chargestat` | `uv tool install chargestat` | `pipx install chargestat` |
| Upgrade | `brew upgrade chargestat` | `uv tool upgrade chargestat` | `pipx upgrade chargestat` |
| Uninstall | `brew uninstall chargestat` | `uv tool uninstall chargestat` | `pipx uninstall chargestat` |

To try it without installing, run `uvx chargestat`. Add `--refresh` to pick up a new release.

![uvx chargestat fetching chargestat from PyPI on first run and printing a snapshot](https://raw.githubusercontent.com/tjdcs/chargestat/main/docs/uvx.gif)

Check the installed version with `chargestat -V`. [CHANGELOG.md](CHANGELOG.md) lists CLI and install changes for each release.

## Usage

```sh
chargestat              # one snapshot
chargestat -w           # live view, refresh every 2 s (Ctrl-C to stop)
chargestat -w 5 -n 12   # 12 refreshes, 5 s apart
chargestat --json       # machine-readable; with -w, one JSON object per line
chargestat -H           # plot charge and battery power over the last 24 h
chargestat -H 6         # ... over the last 6 h (system powerlog keeps ~2-3 days)
```

Exit status is 2 when the Mac has no battery.

## What the rows mean

| Row | Source (`ioreg -rn AppleSmartBattery`) | Notes |
|---|---|---|
| Adapter | `AdapterDetails` | Negotiated USB-PD contract, not live draw. |
| PDOs | `AdapterDetails.UsbHvcMenu` | Fixed-supply PDOs the charger advertises; `[ ]` marks the active one. |
| Rate | `InstantAmperage`, `AppleRawMaxCapacity` | Gauge current into (+) or out of (−) the pack, and the resulting SoC change per hour. |
| Time | `AvgTimeToFull`/`AvgTimeToEmpty`; mAh ÷ mA | macOS's estimate, plus a linear estimate at the present current. The linear one ignores the constant-voltage taper, so it reads short near full. |
| Power | `PowerTelemetryData` | Estimates (`~`). Input = system load + battery branch; "at wall" adds the reported adapter efficiency loss. |
| Battery / Health | `AppleRawCurrentCapacity`, `DesignCapacity`, `CycleCount` | Health is full-charge capacity ÷ design capacity. |
| Updated | `UpdateTime` | The gauge refreshes every ~15–60 s, so consecutive samples often repeat. |

`NotChargingReason` / `SlowChargingReason` are shown as raw hex because Apple doesn't document the bits.

Tested on Apple silicon. Intel Macs report capacities in mAh directly; that path is handled but untested on hardware.

## Development

```sh
uv run chargestat
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

See [RELEASING.md](RELEASING.md) for the PyPI and Homebrew release process.
