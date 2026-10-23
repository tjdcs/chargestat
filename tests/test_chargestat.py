import json
import plistlib
import sqlite3
import subprocess

import pytest

from chargestat import battery, cli, history, plot
from chargestat.render import Style, fmt_minutes, render

NOW = 1_800_000_000


def entry(**overrides):
    """Apple silicon AppleSmartBattery entry, modeled on an M3 Pro while charging."""
    d = {
        "ExternalConnected": True,
        "IsCharging": True,
        "FullyCharged": False,
        "CurrentCapacity": 22,
        "MaxCapacity": 100,
        "AppleRawCurrentCapacity": 1141,
        "AppleRawMaxCapacity": 5318,
        "DesignCapacity": 6249,
        "CycleCount": 437,
        "Voltage": 11439,
        "InstantAmperage": 262,
        "Temperature": 3062,
        "AvgTimeToFull": 680,
        "AvgTimeToEmpty": 65535,
        "UpdateTime": NOW - 12,
        "AdapterDetails": {
            "Watts": 100,
            "AdapterVoltage": 20000,
            "Current": 5000,
            "Description": "pd charger",
            "UsbHvcHvcIndex": 3,
            "UsbHvcMenu": [
                {"Index": 0, "MaxCurrent": 3000, "MaxVoltage": 5000},
                {"Index": 1, "MaxCurrent": 3000, "MaxVoltage": 9000},
                {"Index": 2, "MaxCurrent": 3000, "MaxVoltage": 15000},
                {"Index": 3, "MaxCurrent": 5000, "MaxVoltage": 20000},
            ],
        },
        "ChargerData": {"NotChargingReason": 0, "SlowChargingReason": 0},
        "PowerTelemetryData": {
            "SystemPowerIn": 14042,
            "SystemLoad": 9673,
            "BatteryPower": 4369,
            "AdapterEfficiencyLoss": 879,
            "AccumulatedSystemLoad": 10064208,
        },
    }
    d.update(overrides)
    return d


def unsigned(v):
    return v + (1 << 64) if v < 0 else v


def test_parse_charging():
    s = battery.parse(entry(), now=NOW)
    assert s.adapter.watts == 100
    assert s.adapter.pdos[s.adapter.active_pdo] == (20.0, 5.0)
    assert s.percent == 22
    assert s.current_ma == 262
    assert s.os_minutes_to_full == 680
    assert s.os_minutes_to_empty is None
    assert s.flow.wall == pytest.approx(14.921)
    assert s.temperature_c == pytest.approx(30.62)
    assert s.updated_s_ago == 12
    assert s.health_pct == pytest.approx(100 * 5318 / 6249)
    assert s.minutes_at_current_rate == pytest.approx(60 * (5318 - 1141) / 262)
    assert "AccumulatedSystemLoad" not in s.raw_telemetry
    assert s.adapter_current_a == pytest.approx(14.042 / 20)
    assert s.load_drain_ma is None


def test_parse_discharging_wraps_unsigned():
    s = battery.parse(
        entry(
            ExternalConnected=False,
            IsCharging=False,
            InstantAmperage=unsigned(-1500),
            AvgTimeToFull=65535,
            AvgTimeToEmpty=45,
            PowerTelemetryData={"SystemLoad": 17000, "BatteryPower": unsigned(-17000)},
        ),
        now=NOW,
    )
    assert s.current_ma == -1500
    assert s.discharging
    assert s.adapter.watts is None and s.adapter.pdos == ()
    assert s.flow.battery == -17.0
    assert s.os_minutes_to_empty == 45
    assert s.minutes_at_current_rate == pytest.approx(60 * 1141 / 1500)
    assert s.rate_pct_per_hour == pytest.approx(-100 * 1500 / 5318)
    assert s.adapter_current_a is None
    assert s.load_drain_ma == pytest.approx(-1000 * 17 / 11.439)
    assert s.load_rate_pct_per_hour == pytest.approx(100 * s.load_drain_ma / 5318)
    assert s.load_minutes_to_empty == pytest.approx(60 * 1141 * 11.439 / 17000)


def test_parse_intel_style_capacity():
    d = entry(CurrentCapacity=3000, MaxCapacity=6000)
    del d["AppleRawCurrentCapacity"], d["AppleRawMaxCapacity"]
    s = battery.parse(d, now=NOW)
    assert (s.charge_mah, s.full_mah, s.percent) == (3000, 6000, 50)


def test_parse_minimal_entry():
    s = battery.parse({}, now=NOW)
    assert not s.adapter.connected
    assert s.minutes_at_current_rate is None
    assert render(s, Style(False))


@pytest.mark.parametrize(("m", "out"), [(None, "—"), (5, "5m"), (65, "1h 05m"), (680, "11h 20m")])
def test_fmt_minutes(m, out):
    assert fmt_minutes(m) == out


def test_render_plain():
    text = "\n".join(render(battery.parse(entry(), now=NOW), Style(False)))
    assert "\x1b" not in text
    assert "100 W" in text
    assert "[20V 5A]" in text
    assert "Charging" in text
    assert "11h 20m to full" in text
    assert "~14.0 W in (~0.70 A @ 20 V)" in text
    assert "Drain" not in text


def test_render_drain_on_battery():
    d = entry(
        ExternalConnected=False,
        IsCharging=False,
        InstantAmperage=unsigned(-1500),
        PowerTelemetryData={"SystemLoad": 17000, "BatteryPower": unsigned(-17000)},
    )
    lines = render(battery.parse(d, now=NOW), Style(False))
    drain = next(line for line in lines if line.startswith("Drain"))
    assert "~-1486 mA" in drain and "to empty" in drain


def test_render_states():
    def state(**kw):
        lines = render(battery.parse(entry(**kw), now=NOW), Style(False))
        return next(line for line in lines if line.startswith("Status"))

    assert "On battery" in state(ExternalConnected=False, IsCharging=False)
    assert "Charged" in state(FullyCharged=True, IsCharging=False)
    held = state(IsCharging=False, ChargerData={"NotChargingReason": 0x400})
    assert "not charging" in held and "0x400" in held


def test_read_no_battery(monkeypatch):
    empty = plistlib.dumps([])
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout=empty)
    )
    with pytest.raises(battery.NoBatteryError):
        battery.read()


def test_cli_json(monkeypatch, capsys):
    monkeypatch.setattr(battery, "read", lambda: battery.parse(entry(), now=NOW))
    assert cli.main(["--json"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["adapter"]["watts"] == 100
    assert d["flow"]["wall"] == pytest.approx(14.921)


def test_cli_no_battery_exit_code(monkeypatch, capsys):
    def boom():
        raise battery.NoBatteryError("none")

    monkeypatch.setattr(battery, "read", boom)
    assert cli.main([]) == 2
    assert "none" in capsys.readouterr().err


def powerlog(path, rows):
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE PLBatteryAgent_EventBackward_Battery (timestamp REAL, RawLevel REAL,"
        " Voltage INTEGER, InstantAmperage INTEGER, ExternalConnected INTEGER)"
    )
    con.executemany("INSERT INTO PLBatteryAgent_EventBackward_Battery VALUES (?,?,?,?,?)", rows)
    con.commit()
    con.close()


@pytest.fixture
def log(tmp_path, monkeypatch):
    """Charging at 12 V × 2 A for the last hour, one sample a minute; one older row."""
    path = tmp_path / "Powerlog.PLSQL"
    rows = [(NOW - 7200, 10.0, 11000, -500, 0)]
    rows += [(NOW - 3600 + 60 * i, 20 + i / 3, 12000, 2000, 1) for i in range(61)]
    powerlog(path, rows)
    monkeypatch.setattr(history, "POWERLOG", str(path))
    monkeypatch.setattr(cli.time, "time", lambda: NOW)
    return path


def test_history_read(log):
    samples = history.read(1, now=NOW)
    assert len(samples) == 61
    assert samples[0].t == NOW - 3600 and samples[0].external
    assert samples[0].power == pytest.approx(24)
    assert history.read(3, now=NOW)[0].power == pytest.approx(-5.5)


def test_history_read_missing_voltage(tmp_path, monkeypatch):
    path = tmp_path / "p.PLSQL"
    powerlog(path, [(NOW, 50.0, None, 300, 0), (NOW, 50.0, 11000, -1000, 0)])
    monkeypatch.setattr(history, "POWERLOG", str(path))
    assert [s.power for s in history.read(1, now=NOW)] == [None, pytest.approx(-11)]


def test_history_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "POWERLOG", str(tmp_path / "missing.PLSQL"))
    with pytest.raises(history.HistoryUnavailable):
        history.read(1)
    sqlite3.connect(tmp_path / "empty.PLSQL").execute("CREATE TABLE t (x)").connection.commit()
    monkeypatch.setattr(history, "POWERLOG", str(tmp_path / "empty.PLSQL"))
    with pytest.raises(history.HistoryUnavailable):
        history.read(1)


def test_history_bins_time_weighted():
    def s(t, pct, w):
        return history.Sample(t, pct, w, True)

    # 60 s bins. Bin 0: 50 s at 60 W then a burst of ten 1 s rows at 0 W. Each
    # sample holds until the next row; a 1080 s silence holds only _SAMPLE_S.
    samples = [s(0, 10, 60), *(s(50 + i, 20, 0) for i in range(10)), s(60, 30, 12)]
    samples += [s(240, 40, 12), s(1320, 50, -6)]
    b = history.bins(samples, 0, 1380, 23)
    assert b[0].power == pytest.approx(50)
    assert b[0].percent == pytest.approx((50 * 10 + 10 * 20) / 60)
    assert b[1] == b[2] == b[3] == history.Bin(30, 12, True)
    assert b[4].percent == 40
    assert all(x is None for x in b[5:22])
    assert b[22] == history.Bin(50, -6, True)


def test_canvas():
    top = plot.canvas([100, 100], 0, 100, 2)
    assert top == [[0x01 | 0x08], [0]]
    assert plot.canvas([None, None, 0, None], 0, 100, 1) == [[0, 0x40]]
    # A jump from bottom to top fills the whole column at the second x-pixel.
    assert plot.canvas([0, 100], 0, 100, 1) == [[0x40 | 0x08 | 0x10 | 0x20 | 0x80]]


def test_cli_history_plot(log, capsys):
    assert cli.main(["-H", "1"]) == 0
    out = capsys.readouterr().out
    assert "\x1b" not in out
    assert "Charge" in out and "W, + charging" in out
    assert "  AC " in out and "▀" in out
    assert "+30" in out
    assert "61 powerlog samples" in out and "data starts" not in out


def test_cli_history_json(log, capsys):
    assert cli.main(["-H", "1", "-j"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert len(d) == 61 and d[0]["power"] == pytest.approx(24)


def test_cli_history_errors(tmp_path, monkeypatch, capsys):
    with pytest.raises(SystemExit):
        cli.main(["-H", "-w"])
    monkeypatch.setattr(history, "POWERLOG", str(tmp_path / "missing.PLSQL"))
    assert cli.main(["-H"]) == 2
    assert "cannot read" in capsys.readouterr().err
