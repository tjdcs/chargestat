"""Command-line entry point."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict

from . import __version__, battery, history
from .plot import render_history
from .render import Style, color_enabled, render


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
        type=float,
        const=24.0,
        metavar="HOURS",
        help="plot charge and battery power over the last HOURS (default 24) from the system powerlog",
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


def _history(args: argparse.Namespace, st: Style) -> int:
    end = time.time()
    samples = history.read(args.history, now=end)
    if args.json:
        print(json.dumps([asdict(s) for s in samples]))
    else:
        print("\n".join(render_history(samples, end - 3600 * args.history, end, st)))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.history is not None:
        if args.watch is not None:
            parser.error("--history cannot be combined with --watch")
        if args.history <= 0:
            parser.error("--history HOURS must be positive")
    st = Style(color_enabled() and not args.json)
    if args.history is not None:
        try:
            return _history(args, st)
        except history.HistoryUnavailable as e:
            print(f"chargestat: {e}", file=sys.stderr)
            return 2
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
    return 0
