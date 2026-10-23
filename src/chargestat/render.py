"""Human-readable rendering of a battery Status."""

from __future__ import annotations

import os
import sys

from .battery import Status

_BAR_WIDTH = 20


class Style:
    def __init__(self, enabled: bool):
        self.enabled = enabled

    def _wrap(self, code: str, s: str) -> str:
        return f"\x1b[{code}m{s}\x1b[0m" if self.enabled else s

    def dim(self, s: str) -> str:
        return self._wrap("2", s)

    def bold(self, s: str) -> str:
        return self._wrap("1", s)

    def green(self, s: str) -> str:
        return self._wrap("32", s)

    def yellow(self, s: str) -> str:
        return self._wrap("33", s)

    def red(self, s: str) -> str:
        return self._wrap("31", s)

    def cyan(self, s: str) -> str:
        return self._wrap("36", s)


def color_enabled(stream=sys.stdout) -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return stream.isatty()


def fmt_minutes(m: float | None) -> str:
    if m is None:
        return "—"
    h, m = divmod(round(m), 60)
    return f"{h}h {m:02d}m" if h else f"{m}m"


def level_color(pct: float, st: Style):
    return st.red if pct < 20 else st.yellow if pct < 50 else st.green


def _bar(pct: int, st: Style) -> str:
    filled = round(_BAR_WIDTH * max(0, min(pct, 100)) / 100)
    return level_color(pct, st)("█" * filled) + st.dim("░" * (_BAR_WIDTH - filled))


def _state(s: Status, st: Style) -> str:
    if not s.adapter.connected:
        return st.yellow("On battery")
    if s.fully_charged:
        return st.green("Charged")
    if s.charging:
        text = st.green("Charging")
        if s.slow_charging_reason:
            text += st.yellow(f" (slow, reason 0x{s.slow_charging_reason:x})")
        return text
    text = st.cyan("On adapter, not charging")
    if s.not_charging_reason:
        text += st.dim(f" (reason 0x{s.not_charging_reason:x})")
    return text


def _adapter(s: Status, st: Style) -> str:
    a = s.adapter
    if not a.connected:
        return st.dim("not connected")
    parts = [st.bold(f"{a.watts} W") if a.watts else "connected"]
    if a.description:
        parts.append(a.description)
    if a.voltage_v and a.current_a:
        parts.append(st.dim(f"{a.voltage_v:.1f} V × {a.current_a:.2f} A negotiated"))
    return " · ".join(parts)


def _pdos(s: Status, st: Style) -> str | None:
    a = s.adapter
    if not a.pdos:
        return None
    items = []
    for i, (v, amps) in enumerate(a.pdos):
        item = f"{v:g}V {amps:g}A"
        items.append(st.bold(f"[{item}]") if i == a.active_pdo else st.dim(item))
    return " · ".join(items)


def _rate(s: Status, st: Style) -> str:
    if not s.current_ma:
        return st.dim("idle (0 mA)")
    text = f"{s.current_ma:+d} mA"
    if (r := s.rate_pct_per_hour) is not None:
        text += f" · {r:+.1f} %/h"
    return st.green(text) if s.current_ma > 0 else st.yellow(text)


def _drain(s: Status, st: Style) -> str | None:
    if (ma := s.load_drain_ma) is None:
        return None
    text = f"~{ma:+.0f} mA"
    if (r := s.load_rate_pct_per_hour) is not None:
        text += f" · {r:+.1f} %/h"
    if (m := s.load_minutes_to_empty) is not None:
        text += f" · {fmt_minutes(m)} to empty"
    return text + st.dim(" (system load ÷ pack V)")


def _time(s: Status, st: Style) -> str | None:
    if s.current_ma > 0:
        os_est, target = s.os_minutes_to_full, "to full"
    elif s.current_ma < 0:
        os_est, target = s.os_minutes_to_empty, "to empty"
    else:
        return None
    parts = []
    if os_est is not None:
        parts.append(f"{st.bold(fmt_minutes(os_est))} {target} {st.dim('(macOS)')}")
    if (lin := s.minutes_at_current_rate) is not None:
        parts.append(f"{fmt_minutes(lin)} at current rate")
    return " · ".join(parts) or None


def _power(s: Status, st: Style) -> str | None:
    f = s.flow
    if f.system_load is None:
        return None
    if s.adapter.connected and f.adapter_in:
        text = f"~{f.adapter_in:.1f} W in"
        if (amps := s.adapter_current_a) is not None:
            text += st.dim(f" (~{amps:.2f} A @ {s.adapter.voltage_v:g} V)")
        text += f" → {f.system_load:.1f} W system"
        if f.battery is not None:
            text += f", {f.battery:+.1f} W battery"
        if f.wall is not None:
            text += st.dim(f" · ~{f.wall:.1f} W at wall")
        return text
    return f"~{f.system_load:.1f} W system load"


def _battery(s: Status, st: Style) -> str:
    parts = []
    if s.charge_mah is not None and s.full_mah:
        parts.append(f"{s.charge_mah}/{s.full_mah} mAh")
    if s.voltage_v:
        parts.append(f"{s.voltage_v:.2f} V")
    if s.temperature_c is not None:
        parts.append(f"{s.temperature_c:.1f} °C")
    return " · ".join(parts)


def _health(s: Status, st: Style) -> str | None:
    parts = []
    if (h := s.health_pct) is not None:
        parts.append(f"{h:.0f}% of design ({s.design_mah} mAh)")
    if s.cycle_count is not None:
        parts.append(f"{s.cycle_count} cycles")
    return " · ".join(parts) or None


def render(s: Status, st: Style) -> list[str]:
    rows: list[tuple[str, str | None]] = [
        ("Adapter", _adapter(s, st)),
        ("PDOs", _pdos(s, st)),
        ("Status", f"{_state(s, st)}  {st.bold(f'{s.percent}%')} {_bar(s.percent, st)}"),
        ("Rate", _rate(s, st)),
        ("Drain", _drain(s, st)),
        ("Time", _time(s, st)),
        ("Power", _power(s, st)),
        ("Battery", _battery(s, st)),
        ("Health", _health(s, st)),
    ]
    if s.updated_s_ago is not None:
        rows.append(("Updated", st.dim(f"{s.updated_s_ago:.0f} s ago by battery gauge")))
    return [f"{st.dim(f'{label:<8}')} {value}" for label, value in rows if value]
