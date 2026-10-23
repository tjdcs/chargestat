# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`chargestat` is a macOS-only, read-only CLI (Python, stdlib only) that reports power adapter contract, charge rate, power flow, and time to full/empty from the `AppleSmartBattery` IORegistry node. Distributed via PyPI (`uvx chargestat`) and a Homebrew tap (`tjdcs/tap`); see RELEASING.md.

## Commands

```sh
uv run chargestat [-w [SEC]] [-n N] [--json] [-H [HOURS]]
uv run pytest                          # all tests
uv run pytest -k discharging           # single test
uv run ruff check . && uv run ruff format --check .
uv run --isolated --python 3.10 --with pytest pytest   # oldest supported Python
```

## Architecture

- `battery.py` — runs `ioreg -rn AppleSmartBattery -a` (plist output, parsed with `plistlib`, no regex) and `parse()`s one entry into a frozen `Status`. `parse()` takes a plain dict plus `now`, so tests feed synthetic dicts; keep hardware access confined to `read()`.
- `render.py` — `render(Status, Style) -> list[str]`; each row is a small function returning `None` to omit the row. `Style` handles ANSI (respects `NO_COLOR`/`FORCE_COLOR`).
- `history.py` — `read()` queries the system powerlog (`sqlite3`, `mode=ro`) into `Sample`s; `bins()` takes time-weighted means per x-pixel (each row holds until the next, since rows are event-driven and cluster around state changes); silences > 15 min become `None` gaps.
- `plot.py` — stdlib braille line charts (2×4 dots per cell) for `-H`: charge %, battery power (W, gauge V × I), adapter strip, local-time axis.
- `cli.py` — `_with_average()` attaches the powerlog's recent mean discharge current to `Status` (on battery only; skipped silently if the powerlog is unreadable); argparse, watch loop (redraws in place on a TTY by moving the cursor up the previous block's line count), `--json` (NDJSON in watch mode; a JSON array of samples with `-H`), `-H` history plots.

## Data caveats (verified on M3 Pro, macOS 26)

- Signed values (`InstantAmperage`, telemetry `BatteryPower` when discharging) arrive as unsigned 64-bit; `_signed()` converts. Apply it to any new signed key.
- Apple silicon: `CurrentCapacity`/`MaxCapacity` are percentages; mAh is in `AppleRaw*Capacity`. Intel reports mAh in `CurrentCapacity`/`MaxCapacity` (handled, untested on hardware).
- `PowerTelemetryData`: `SystemPowerIn == SystemLoad + BatteryPower` exactly. Its `BatteryPower` differs substantially from gauge `Voltage × InstantAmperage`; the Power row uses telemetry, Rate/Time use gauge current. `SystemVoltageIn`/`SystemCurrentIn` are not bus V/A (≈4 V on a 20 V contract), so they're only exposed raw in JSON.
- The active PD contract is `AdapterDetails.UsbHvcMenu[UsbHvcHvcIndex]`. Index 255 means no contract: VBUS falls back to 5 V (seen with `AdapterPowerTier` 1, ~13 W in). `AdapterVoltage`/`Current` are the adapter rating and stay at 20 V × 5 A through the fallback, so never present them as negotiated.
- Gauge values refresh every ~15–60 s (`UpdateTime`); repeated samples are expected. `PowerTelemetryData` refreshes on the same tick, so it is not a faster source.
- Time fields use 65535 (and 0) for "unknown".
- Time to empty: gauge `InstantAmperage` and telemetry `SystemLoad` are single readings, and `AvgTimeToEmpty` averages over a short, undocumented window (it moved from 376 to 99 min in ~2 min under a build). The Time row leads with remaining mAh ÷ the 15-min time-weighted mean gauge current from the powerlog, clipped to the time since unplug; macOS is shown alongside. Time to full is macOS only, because it models the constant-voltage taper.
- History: `/private/var/db/powerlog/Library/BatteryLife/CurrentPowerlog.PLSQL` (world-readable, private schema), table `PLBatteryAgent_EventBackward_Battery`, a row every ~15 s including through sleep. The current DB holds ~2–3 days; older days are gzipped in `Archives/` (not read). `RawLevel` is the gauge % (`AppleRawCurrentCapacity/AppleRawMaxCapacity`, e.g. 97.7 while the UI `Level` shows 100). `InstantAmperage` is stored already signed. `pmset -g log` is too sparse to plot (event-driven integer %, hours-long gaps).

## Packaging constraints

- Keep zero runtime dependencies; the Homebrew formula (`packaging/homebrew/chargestat.rb`) has no `resource` blocks.
- Build backend must stay pure Python (`flit_core`): Homebrew builds from source with `--no-binary :all:`, and `uv_build` would need Rust.
- Version lives only in `pyproject.toml`; `__version__` reads installed metadata. The release workflow fails if the tag ≠ `v<version>`.
