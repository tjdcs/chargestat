"""Read adapter and battery state from the AppleSmartBattery IORegistry node."""

from __future__ import annotations

import plistlib
import subprocess
import time
from dataclasses import asdict, dataclass

# AvgTimeToFull / AvgTimeToEmpty / TimeRemaining use this for "unknown".
_UNKNOWN_MINUTES = 65535


class NoBatteryError(RuntimeError):
    pass


def _signed(v: int | None) -> int | None:
    """ioreg reports signed 64-bit values (e.g. discharge current) as unsigned."""
    if v is None:
        return None
    return v - (1 << 64) if v >= (1 << 63) else v


def _scaled(v: int | None, div: float = 1000) -> float | None:
    return None if v is None else v / div


def _minutes(v: int | None) -> int | None:
    return None if v in (None, 0, _UNKNOWN_MINUTES) else v


@dataclass(frozen=True)
class Adapter:
    connected: bool
    watts: int | None
    voltage_v: float | None
    current_a: float | None
    description: str | None
    # Source capabilities advertised by the charger: (volts, amps) per PDO.
    pdos: tuple[tuple[float, float], ...] = ()
    active_pdo: int | None = None


@dataclass(frozen=True)
class PowerFlow:
    """PowerTelemetryData estimates, in W. ``adapter_in == system_load + battery``."""

    adapter_in: float | None
    system_load: float | None
    battery: float | None
    adapter_loss: float | None

    @property
    def wall(self) -> float | None:
        if self.adapter_in is None or self.adapter_loss is None:
            return None
        return self.adapter_in + self.adapter_loss


@dataclass(frozen=True)
class Status:
    adapter: Adapter
    flow: PowerFlow
    charging: bool
    fully_charged: bool
    percent: int
    charge_mah: int | None
    full_mah: int | None
    design_mah: int | None
    cycle_count: int | None
    voltage_v: float | None
    current_ma: int
    temperature_c: float | None
    os_minutes_to_full: int | None
    os_minutes_to_empty: int | None
    not_charging_reason: int
    slow_charging_reason: int
    updated_s_ago: float | None
    raw_telemetry: dict[str, int]

    @property
    def discharging(self) -> bool:
        return self.current_ma < 0

    @property
    def health_pct(self) -> float | None:
        if not self.full_mah or not self.design_mah:
            return None
        return 100 * self.full_mah / self.design_mah

    @property
    def rate_pct_per_hour(self) -> float | None:
        """Signed SoC change per hour at the present gauge current."""
        if not self.full_mah or not self.current_ma:
            return None
        return 100 * self.current_ma / self.full_mah

    @property
    def minutes_at_current_rate(self) -> float | None:
        """Linear time to full (charging) or empty (discharging) at the present current.

        Ignores the constant-voltage taper near full, so it under-estimates charge
        time above ~80 %.
        """
        if self.charge_mah is None or not self.full_mah or not self.current_ma:
            return None
        remaining = self.full_mah - self.charge_mah if self.current_ma > 0 else self.charge_mah
        return 60 * remaining / abs(self.current_ma)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["flow"]["wall"] = self.flow.wall
        d |= {
            "discharging": self.discharging,
            "health_pct": self.health_pct,
            "rate_pct_per_hour": self.rate_pct_per_hour,
            "minutes_at_current_rate": self.minutes_at_current_rate,
        }
        return d


def parse(entry: dict, now: float | None = None) -> Status:
    """Build a Status from one AppleSmartBattery entry of ``ioreg -a`` output."""
    tel = {k: _signed(v) for k, v in entry.get("PowerTelemetryData", {}).items()}
    det = entry.get("AdapterDetails", {})
    chg = entry.get("ChargerData", {})
    connected = bool(entry.get("ExternalConnected"))
    current = _signed(entry.get("InstantAmperage", entry.get("Amperage"))) or 0
    temp = entry.get("Temperature")
    update = entry.get("UpdateTime")
    now = time.time() if now is None else now

    # On Apple silicon CurrentCapacity/MaxCapacity are percentages and the
    # mAh figures live in the AppleRaw* keys; Intel reports mAh directly.
    raw_max = entry.get("AppleRawMaxCapacity")
    if raw_max is not None:
        charge_mah, full_mah = entry.get("AppleRawCurrentCapacity"), raw_max
        percent = entry.get("CurrentCapacity", 0)
    else:
        charge_mah, full_mah = entry.get("CurrentCapacity"), entry.get("MaxCapacity")
        percent = round(100 * charge_mah / full_mah) if charge_mah and full_mah else 0

    return Status(
        adapter=Adapter(
            connected=connected,
            watts=det.get("Watts") if connected else None,
            voltage_v=_scaled(det.get("AdapterVoltage")) if connected else None,
            current_a=_scaled(det.get("Current")) if connected else None,
            description=det.get("Description") if connected else None,
            pdos=tuple(
                (m["MaxVoltage"] / 1000, m["MaxCurrent"] / 1000) for m in det.get("UsbHvcMenu", [])
            )
            if connected
            else (),
            active_pdo=det.get("UsbHvcHvcIndex") if connected else None,
        ),
        flow=PowerFlow(
            adapter_in=_scaled(tel.get("SystemPowerIn")),
            system_load=_scaled(tel.get("SystemLoad")),
            battery=_scaled(tel.get("BatteryPower")),
            adapter_loss=_scaled(tel.get("AdapterEfficiencyLoss")),
        ),
        charging=bool(entry.get("IsCharging")),
        fully_charged=bool(entry.get("FullyCharged")),
        percent=percent,
        charge_mah=charge_mah,
        full_mah=full_mah,
        design_mah=entry.get("DesignCapacity"),
        cycle_count=entry.get("CycleCount"),
        voltage_v=_scaled(entry.get("Voltage")),
        current_ma=current,
        temperature_c=_scaled(temp, 100),
        os_minutes_to_full=_minutes(entry.get("AvgTimeToFull")),
        os_minutes_to_empty=_minutes(entry.get("AvgTimeToEmpty")),
        not_charging_reason=chg.get("NotChargingReason", 0),
        slow_charging_reason=chg.get("SlowChargingReason", 0),
        updated_s_ago=max(0.0, now - update) if update else None,
        raw_telemetry={k: v for k, v in tel.items() if not k.startswith("Accumulated")},
    )


def read() -> Status:
    out = subprocess.run(
        ["ioreg", "-rn", "AppleSmartBattery", "-a"],
        capture_output=True,
        check=True,
    ).stdout
    entries = plistlib.loads(out) if out.strip() else []
    if not entries:
        raise NoBatteryError("no AppleSmartBattery found (desktop Mac?)")
    return parse(entries[0])
