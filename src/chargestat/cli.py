"""Command-line entry point."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time

from . import __version__, battery
from .render import Style, color_enabled, render

_TRANSITION = re.compile(r"^(\S+ \S+) .*Using (AC|Batt)\(Charge: ?(\d+)\)")


def recent_transitions(n: int) -> list[str]:
    """Last ``n`` AC/battery switches from the power-management log."""
    log = subprocess.run(["pmset", "-g", "log"], check=False, capture_output=True, text=True).stdout
    hits = [m for line in log.splitlines() if (m := _TRANSITION.match(line))]
    return [f"{m[1]}  {'adapter' if m[2] == 'AC' else 'battery'} at {m[3]}%" for m in hits[-n:]]


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="chargestat",
        description="Show Mac power adapter, charge rate, and time to full/empty.",
    )
    p.add_argument(
        "-w",
        "--watch",
        nargs="?",
        type=float,
        const=2.0,
        metavar="SECONDS",
        help="refresh continuously (default every 2 s; the gauge itself updates every ~15-60 s)",
    )
    p.add_argument("-n", "--count", type=int, help="stop after N refreshes in watch mode")
    p.add_argument(
        "-j", "--json", action="store_true", help="print JSON (one object per line in watch mode)"
    )
    p.add_argument(
        "-H",
        "--history",
        nargs="?",
        type=int,
        const=5,
        metavar="N",
        help="also list the last N adapter/battery switches (default 5)",
    )
    p.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    return p


def _emit(args: argparse.Namespace, st: Style, redraw_lines: int) -> int:
    s = battery.read()
    if args.json:
        print(json.dumps(s.to_dict()), flush=True)
        return 0
    lines = render(s, st)
    if redraw_lines:
        # Move to the start of the previous block and clear to end of screen.
        sys.stdout.write(f"\x1b[{redraw_lines}F\x1b[J")
    print("\n".join(lines), flush=True)
    return len(lines)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    st = Style(color_enabled() and not args.json)
    try:
        if args.watch is None:
            _emit(args, st, 0)
        else:
            redraw = sys.stdout.isatty() and not args.json
            drawn, i = 0, 0
            while True:
                drawn = _emit(args, st, drawn if redraw else 0)
                i += 1
                if args.count and i >= args.count:
                    break
                if not redraw and not args.json:
                    print()
                time.sleep(args.watch)
    except battery.NoBatteryError as e:
        print(f"chargestat: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    if args.history and not args.json:
        print()
        for line in recent_transitions(args.history):
            print(st.dim(line))
    return 0
