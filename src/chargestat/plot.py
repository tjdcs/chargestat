"""Braille line charts of charge history."""

from __future__ import annotations

import math
import shutil
import time
from collections.abc import Callable, Sequence

from .history import Sample, bins
from .render import Style, level_color

# Dot bit for (x, y) within a braille cell: x in 0..1, y in 0..3 from the top.
_DOTS = ((0x01, 0x02, 0x04, 0x40), (0x08, 0x10, 0x20, 0x80))
_LABEL_W = 5
_GUTTER = _LABEL_W + 2  # label, space, axis edge
_CHARGE_ROWS = 8
_POWER_ROWS = 6
_TICK_STEPS_S = (300, 600, 900, 1800, 3600, 7200, 10800, 21600, 43200, 86400)

Values = Sequence[float | None]


def _y(v: float, lo: float, hi: float, height: int) -> int:
    f = (hi - v) / (hi - lo) if hi > lo else 0.5
    return max(0, min(height - 1, round(f * (height - 1))))


def canvas(values: Values, lo: float, hi: float, rows: int) -> list[list[int]]:
    """Braille dot masks, ``rows`` × ceil(len(values) / 2), for one value per x-pixel.

    Consecutive points are joined by filling the vertical span between them;
    ``None`` breaks the line.
    """
    height = 4 * rows
    cells = [[0] * math.ceil(len(values) / 2) for _ in range(rows)]
    prev = None
    for x, v in enumerate(values):
        if v is None:
            prev = None
            continue
        y = _y(v, lo, hi, height)
        top, bottom = (y, y) if prev is None else (min(prev, y), max(prev, y))
        for yy in range(top, bottom + 1):
            cells[yy // 4][x // 2] |= _DOTS[x % 2][yy % 4]
        prev = y
    return cells


def _pairs(values: Values) -> list[list[float]]:
    """Non-None values under each character column."""
    return [[v for v in values[i : i + 2] if v is not None] for i in range(0, len(values), 2)]


def chart(
    values: Values,
    lo: float,
    hi: float,
    rows: int,
    st: Style,
    *,
    ticks: Sequence[float],
    fmt: Callable[[float], str],
    color_of: Callable[[float], Callable[[str], str]],
    zero_line: bool = False,
) -> list[str]:
    height = 4 * rows
    cells = canvas(values, lo, hi, rows)
    labels = {_y(t, lo, hi, height) // 4: fmt(t) for t in ticks}
    means = [sum(p) / len(p) if p else None for p in _pairs(values)]
    zero_row = zero_mask = None
    if zero_line and lo <= 0 <= hi:
        y = _y(0, lo, hi, height)
        zero_row, zero_mask = y // 4, _DOTS[0][y % 4] | _DOTS[1][y % 4]
    lines = []
    for r, row in enumerate(cells):
        out = []
        for c, mask in enumerate(row):
            if mask:
                out.append(color_of(means[c])(chr(0x2800 + mask)))
            elif r == zero_row:
                out.append(st.dim(chr(0x2800 + zero_mask)))
            else:
                out.append(" ")
        edge = "┤" if r in labels else "│"
        lines.append(st.dim(f"{labels.get(r, ''):>{_LABEL_W}} {edge}") + "".join(out))
    return lines


def time_axis(start: float, end: float, cols: int, st: Style) -> list[str]:
    """Axis rule and local-time tick labels under ``cols`` character columns."""
    span = end - start
    fmt = "%a %H:%M" if span > 86400 else "%H:%M"
    spacing = len(time.strftime(fmt)) + 3
    step = next(
        (s for s in _TICK_STEPS_S if span / s <= cols / spacing),
        86400 * math.ceil(span / 86400 * spacing / cols),
    )
    rule, text = ["─"] * cols, [" "] * cols
    off = time.localtime(start).tm_gmtoff
    t = (math.floor((start + off) / step) + 1) * step - off
    while t < end:
        c = int((t - start) / span * cols)
        label = time.strftime(fmt, time.localtime(t))
        left = c - len(label) // 2
        rule[c] = "┬"
        if left >= 0 and left + len(label) <= cols:
            text[left : left + len(label)] = label
        t += step
    pad = " " * _LABEL_W
    return [st.dim(f"{pad} └{''.join(rule)}"), st.dim(f"{pad}  {''.join(text)}")]


def adapter_strip(states: Sequence[bool | None], st: Style) -> str:
    """One row marking the columns where the adapter was connected."""
    cells = "".join(st.cyan("▀") if s else " " for s in states)
    return st.dim(f"{'AC':>{_LABEL_W}}  ") + cells


def _nice(x: float) -> float:
    """Smallest 1, 2 or 5 × 10ⁿ that is ≥ ``x``."""
    if x <= 0:
        return 1.0
    e = 10 ** math.floor(math.log10(x))
    return next(m * e for m in (1, 2, 5, 10) if m * e >= x)


def _signed_range(values: Sequence[float]) -> tuple[float, float]:
    lo, hi = min(0.0, *values), max(0.0, *values)
    step = _nice((hi - lo) / 4)
    lo, hi = math.floor(lo / step) * step, math.ceil(hi / step) * step
    return lo, max(hi, lo + step)


def _signed_label(v: float) -> str:
    return f"{v:+g}" if v else "0"


def render_history(
    samples: Sequence[Sample], start: float, end: float, st: Style, columns: int | None = None
) -> list[str]:
    if not samples:
        return [st.dim("no powerlog samples in this window")]
    columns = columns or shutil.get_terminal_size((80, 24)).columns
    cols = max(10, columns - _GUTTER)
    bs = bins(list(samples), start, end, 2 * cols)
    percent = [b.percent if b else None for b in bs]
    power = [b.power if b else None for b in bs]
    lo, hi = _signed_range([w for w in power if w is not None])

    def power_color(w: float) -> Callable[[str], str]:
        return st.green if w > 0 else st.yellow if w < 0 else st.dim

    lines = [st.bold("Charge") + st.dim("  gauge %")]
    lines += chart(
        percent,
        0,
        100,
        _CHARGE_ROWS,
        st,
        ticks=(100, 50, 0),
        fmt=lambda v: f"{v:g}",
        color_of=lambda p: level_color(p, st),
    )
    lines.append(st.bold("Battery") + st.dim("  W, + charging, gauge V × I"))
    lines += chart(
        power,
        lo,
        hi,
        _POWER_ROWS,
        st,
        ticks=(hi, 0, lo),
        fmt=_signed_label,
        color_of=power_color,
        zero_line=True,
    )
    states = [next((b.external for b in bs[i : i + 2] if b), None) for i in range(0, len(bs), 2)]
    lines.append(adapter_strip(states, st))
    lines += time_axis(start, end, cols, st)
    footer = f"{len(samples)} powerlog samples"
    if samples[0].t > start + (end - start) / cols:
        footer += f" · data starts {time.strftime('%a %H:%M', time.localtime(samples[0].t))}"
    lines.append(st.dim(footer))
    return lines
