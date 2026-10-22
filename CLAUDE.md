# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`chargewatch` is a single macOS-only Bash script that samples charger input and battery power from the `AppleSmartBattery` IORegistry node, then prints the negotiated adapter contract and recent AC/battery transitions from `pmset`. There is no build, test suite, or linter configured.

## Running

```sh
./chargewatch            # 3 samples, 1.5 s apart
./chargewatch 10 5       # 10 samples, 5 s apart
```

Needs real hardware with a battery; output on a desktop Mac will be zeros/`none`.

## Implementation notes

- Shebang is `/bin/bash`, which on macOS is Bash 3.2. Avoid Bash 4+ features (associative arrays, `${var,,}`, `mapfile`, `|&`, etc.).
- All metrics come from one `ioreg -rn AppleSmartBattery` dump per sample, held in `$dump` and read by `field()`. Add new columns by calling `field <IORegKey>` and extending both `printf` format strings (header and row) in step.
- `ioreg` prints signed values (e.g. `InstantAmperage`, `BatteryPower` while discharging) as unsigned 64-bit; `field()` relies on `$((...))` wrapping them back to signed. Don't route raw values through `bc` or `printf %u` before that conversion.
- Most `System*`/`BatteryPower` keys are in mV/mA/mW and are scaled to V/A/W with `bc`. `InstantAmperage` stays in mA; `NotChargingReason` is shown as hex.
- The battery controller refreshes these values only every ~15 s, so identical consecutive samples are expected, not a bug.
- The trailing `pmset` section parses human-readable output with `grep`/`sed`; those regexes are tied to current macOS `pmset` formatting.
