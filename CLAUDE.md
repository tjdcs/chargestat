# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`chargewatch` is a macOS-only, read-only CLI (Python, stdlib only) that reports power adapter contract, charge rate, power flow, and time to full/empty from the `AppleSmartBattery` IORegistry node. Distributed via PyPI (`uvx chargewatch`) and a Homebrew tap (`tjdcs/tap`); see RELEASING.md.

## Commands

```sh
uv run chargewatch [-w [SEC]] [-n N] [--json] [-H [N]]
uv run pytest                          # all tests
uv run pytest -k discharging           # single test
uv run ruff check . && uv run ruff format --check .
uv run --isolated --python 3.10 --with pytest pytest   # oldest supported Python
```

## Architecture

- `battery.py` — runs `ioreg -rn AppleSmartBattery -a` (plist output, parsed with `plistlib`, no regex) and `parse()`s one entry into a frozen `Status`. `parse()` takes a plain dict plus `now`, so tests feed synthetic dicts; keep hardware access confined to `read()`.
- `render.py` — `render(Status, Style) -> list[str]`; each row is a small function returning `None` to omit the row. `Style` handles ANSI (respects `NO_COLOR`/`FORCE_COLOR`).
- `cli.py` — argparse, watch loop (redraws in place on a TTY by moving the cursor up the previous block's line count), `--json` (NDJSON in watch mode), `pmset -g log` history.

## Data caveats (verified on M3 Pro, macOS 26)

- Signed values (`InstantAmperage`, telemetry `BatteryPower` when discharging) arrive as unsigned 64-bit; `_signed()` converts. Apply it to any new signed key.
- Apple silicon: `CurrentCapacity`/`MaxCapacity` are percentages; mAh is in `AppleRaw*Capacity`. Intel reports mAh in `CurrentCapacity`/`MaxCapacity` (handled, untested on hardware).
- `PowerTelemetryData`: `SystemPowerIn == SystemLoad + BatteryPower` exactly. Its `BatteryPower` differs substantially from gauge `Voltage × InstantAmperage`; the Power row uses telemetry, Rate/Time use gauge current. `SystemVoltageIn`/`SystemCurrentIn` are not bus V/A (≈4 V on a 20 V contract), so they're only exposed raw in JSON.
- The active PD contract is `AdapterDetails.UsbHvcMenu[UsbHvcHvcIndex]`.
- Gauge values refresh every ~15–60 s (`UpdateTime`); repeated samples are expected. `PowerTelemetryData` refreshes on the same tick, so it is not a faster source.
- Time fields use 65535 (and 0) for "unknown".

## Packaging constraints

- Keep zero runtime dependencies; the Homebrew formula (`packaging/homebrew/chargewatch.rb`) has no `resource` blocks.
- Build backend must stay pure Python (`flit_core`): Homebrew builds from source with `--no-binary :all:`, and `uv_build` would need Rust.
- Version lives only in `pyproject.toml`; `__version__` reads installed metadata. The release workflow fails if the tag ≠ `v<version>`.
