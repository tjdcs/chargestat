"""Charge history from the system powerlog."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

# World-readable SQLite store kept by the PowerLog agent; private, undocumented schema.
POWERLOG = "/private/var/db/powerlog/Library/BatteryLife/CurrentPowerlog.PLSQL"
_QUERY = (
    "SELECT timestamp, RawLevel, Voltage, InstantAmperage, ExternalConnected"
    " FROM PLBatteryAgent_EventBackward_Battery WHERE timestamp >= ? ORDER BY timestamp"
)
# Rows are event-driven: ~30 s apart when steady, ~1 s apart around state changes,
# and they continue through sleep. A longer silence is a real gap.
_MAX_GAP_S = 900
_SAMPLE_S = 15


class HistoryUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class Sample:
    t: float
    percent: float
    power: float | None  # W into (+) or out of (−) the pack: gauge V × I
    external: bool


@dataclass(frozen=True)
class Bin:
    percent: float
    power: float | None
    external: bool


def _sample(t, level, mv, ma, external) -> Sample:
    # SQLite integers are signed 64-bit, so no _signed() wrap is needed here.
    power = mv * ma / 1e6 if mv is not None and ma is not None else None
    return Sample(t, level, power, bool(external))


def read(hours: float, now: float | None = None) -> list[Sample]:
    """Powerlog battery samples from the last ``hours``, oldest first."""
    now = time.time() if now is None else now
    try:
        con = sqlite3.connect(f"{Path(POWERLOG).as_uri()}?mode=ro", uri=True)
        try:
            rows = con.execute(_QUERY, (now - 3600 * hours,)).fetchall()
        finally:
            con.close()
    except sqlite3.Error as e:
        raise HistoryUnavailable(f"cannot read {POWERLOG}: {e}") from e
    return [_sample(*r) for r in rows if r[1] is not None]


def bins(samples: list[Sample], start: float, end: float, n: int) -> list[Bin | None]:
    """Time-weighted means over ``n`` equal bins between ``start`` and ``end``.

    Each sample holds until the next row (zero-order hold), so bursts of rows
    around state changes don't outweigh steady stretches. A hold longer than
    ``_MAX_GAP_S`` (powerlog off, machine shut down) shrinks to ``_SAMPLE_S``,
    leaving the bins it spans ``None``.
    """
    width = (end - start) / n
    held = [0.0] * n
    percent = [0.0] * n
    power_held = [0.0] * n
    power = [0.0] * n
    external = [0.0] * n
    for s, nxt in zip(samples, [s.t for s in samples[1:]] + [end]):
        a = max(s.t, start)
        b = min(nxt if nxt - s.t <= _MAX_GAP_S else s.t + _SAMPLE_S, end)
        for i in range(int((a - start) / width), min(n, int((b - start) / width) + 1)):
            lo = start + i * width
            w = min(b, lo + width) - max(a, lo)
            if w <= 0:
                continue
            held[i] += w
            percent[i] += w * s.percent
            external[i] += w * s.external
            if s.power is not None:
                power_held[i] += w
                power[i] += w * s.power
    return [
        Bin(
            percent[i] / held[i],
            power[i] / power_held[i] if power_held[i] else None,
            2 * external[i] >= held[i],
        )
        if held[i]
        else None
        for i in range(n)
    ]
