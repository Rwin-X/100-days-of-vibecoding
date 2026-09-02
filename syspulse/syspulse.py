#!/usr/bin/env python3
"""
SysPulse — Phosphor-terminal system resource monitor.

A real-time CPU / memory / disk / network monitor rendered in a
CRT-green terminal aesthetic, built with PyQt6 + pyqtgraph.

Author: Rwin-x (devforge)
"""

import sys
import time
import platform
from collections import deque
from datetime import datetime

import psutil
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QLinearGradient, QFontDatabase
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QFrame, QProgressBar, QSizePolicy, QScrollArea
)
import pyqtgraph as pg


# ----------------------------------------------------------------------
# Palette / theme constants
# ----------------------------------------------------------------------

BG = "#04070a"
PANEL_BG = "#070c0e"
PANEL_BORDER = "#123329"
GREEN = "#39ff8f"
GREEN_DIM = "#1c8055"
GREEN_FAINT = "#0f4a33"
CYAN = "#3ff0ff"
AMBER = "#ffb02e"
RED = "#ff4d4d"
TEXT_DIM = "#5c8a76"
TEXT_FAINT = "#2e5443"

FONT_FAMILY = "JetBrains Mono"

HISTORY_LEN = 90  # data points kept per graph (~90s at 1Hz)


def load_mono_font() -> str:
    """Pick the best available monospace font on this system."""
    families = set(QFontDatabase.families())
    for candidate in ("JetBrains Mono", "Cascadia Mono", "Consolas",
                       "DejaVu Sans Mono", "Liberation Mono", "Courier New"):
        if candidate in families:
            return candidate
    return "monospace"


def level_color(pct: float) -> str:
    """Return a status color based on load percentage."""
    if pct >= 90:
        return RED
    if pct >= 70:
        return AMBER
    return GREEN


# ----------------------------------------------------------------------
# Background sampler — keeps psutil polling off the UI thread
# ----------------------------------------------------------------------

class SystemSampler(QObject):
    sample_ready = pyqtSignal(dict)

    def __init__(self, interval_ms: int = 1000):
        super().__init__()
        self.interval_ms = interval_ms
        self._running = True
        self._last_net = psutil.net_io_counters()
        self._last_time = time.time()
        # Prime per-cpu percent (first call always returns 0.0)
        psutil.cpu_percent(percpu=True)
        psutil.cpu_percent()

    def stop(self):
        self._running = False

    def run(self):
        while self._running:
            data = self._sample()
            self.sample_ready.emit(data)
            QThread.msleep(self.interval_ms)

    def _sample(self) -> dict:
        now = time.time()
        dt = max(now - self._last_time, 1e-6)

        cpu_total = psutil.cpu_percent()
        cpu_per_core = psutil.cpu_percent(percpu=True)

        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()

        net = psutil.net_io_counters()
        up_rate = (net.bytes_sent - self._last_net.bytes_sent) / dt
        down_rate = (net.bytes_recv - self._last_net.bytes_recv) / dt
        self._last_net = net
        self._last_time = now

        disk_usage = {}
        try:
            for part in psutil.disk_partitions(all=False):
                if not part.mountpoint:
                    continue
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    disk_usage[part.mountpoint] = usage
                except (PermissionError, OSError):
                    continue
        except Exception:
            pass

        try:
            freq = psutil.cpu_freq()
        except Exception:
            freq = None

        try:
            temps = psutil.sensors_temperatures()
        except (AttributeError, Exception):
            temps = {}

        try:
            boot_ts = psutil.boot_time()
        except Exception:
            boot_ts = None

        try:
            procs = len(psutil.pids())
        except Exception:
            procs = 0

        top_procs = self._top_processes()

        return {
            "t": now,
            "cpu_total": cpu_total,
            "cpu_per_core": cpu_per_core,
            "cpu_freq": freq,
            "mem_percent": vm.percent,
            "mem_used": vm.used,
            "mem_total": vm.total,
            "mem_available": vm.available,
            "swap_percent": swap.percent,
            "swap_used": swap.used,
            "swap_total": swap.total,
            "net_up": up_rate,
            "net_down": down_rate,
            "net_up_total": net.bytes_sent,
            "net_down_total": net.bytes_recv,
            "disk_usage": disk_usage,
            "temps": temps,
            "boot_ts": boot_ts,
            "proc_count": procs,
            "top_procs": top_procs,
        }

    def _top_processes(self, limit: int = 6):
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = p.info
                if info["cpu_percent"] is None:
                    continue
                procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        procs.sort(key=lambda x: x.get("cpu_percent") or 0, reverse=True)
        return procs[:limit]


# ----------------------------------------------------------------------
# Reusable UI atoms
# ----------------------------------------------------------------------

class Panel(QFrame):
    """A bordered CRT-style panel with a title bar."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("Panel")
        self.setStyleSheet(f"""
            #Panel {{
                background-color: {PANEL_BG};
                border: 1px solid {PANEL_BORDER};
                border-radius: 2px;
            }}
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QLabel(f"  {title}")
        header.setFixedHeight(26)
        header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        header.setStyleSheet(f"""
            color: {GREEN};
            background-color: {GREEN_FAINT};
            font-family: '{FONT_FAMILY}';
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 2px;
            padding: 5px 6px;
            border-bottom: 1px solid {PANEL_BORDER};
        """)
        outer.addWidget(header)

        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(12, 10, 12, 12)
        self.body_layout.setSpacing(8)
        outer.addWidget(self.body, 1)


class MetricBar(QWidget):
    """A labeled percentage bar: NAME  [#######.......]  73.2%"""

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.name_lbl = QLabel(label)
        self.name_lbl.setFixedWidth(56)
        self.name_lbl.setStyleSheet(
            f"color:{TEXT_DIM}; font-family:'{FONT_FAMILY}'; font-size:11px;"
        )

        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(14)
        self._apply_bar_style(GREEN)

        self.pct_lbl = QLabel("0.0%")
        self.pct_lbl.setFixedWidth(52)
        self.pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.pct_lbl.setStyleSheet(
            f"color:{GREEN}; font-family:'{FONT_FAMILY}'; font-size:11px; font-weight:600;"
        )

        layout.addWidget(self.name_lbl)
        layout.addWidget(self.bar, 1)
        layout.addWidget(self.pct_lbl)

    def _apply_bar_style(self, color: str):
        self.bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {BG};
                border: 1px solid {PANEL_BORDER};
                border-radius: 1px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
            }}
        """)

    def set_value(self, pct: float):
        pct = max(0.0, min(100.0, pct))
        self.bar.setValue(int(pct * 10))
        self.pct_lbl.setText(f"{pct:5.1f}%")
        color = level_color(pct)
        self.pct_lbl.setStyleSheet(
            f"color:{color}; font-family:'{FONT_FAMILY}'; font-size:11px; font-weight:600;"
        )
        self._apply_bar_style(color)


class StatRow(QWidget):
    """A simple label: value row for text stats."""

    def __init__(self, label: str, value: str = "--", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.name_lbl = QLabel(label)
        self.name_lbl.setStyleSheet(
            f"color:{TEXT_DIM}; font-family:'{FONT_FAMILY}'; font-size:11px;"
        )
        self.value_lbl = QLabel(value)
        self.value_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.value_lbl.setStyleSheet(
            f"color:{CYAN}; font-family:'{FONT_FAMILY}'; font-size:11px; font-weight:600;"
        )
        layout.addWidget(self.name_lbl)
        layout.addStretch(1)
        layout.addWidget(self.value_lbl)

    def set_value(self, text: str, color: str = CYAN):
        self.value_lbl.setText(text)
        self.value_lbl.setStyleSheet(
            f"color:{color}; font-family:'{FONT_FAMILY}'; font-size:11px; font-weight:600;"
        )


def make_plot(y_max=100, y_label="%", fill_color=GREEN) -> tuple[pg.PlotWidget, pg.PlotDataItem]:
    """Build a themed pyqtgraph strip-chart with a glow-filled line."""
    plot = pg.PlotWidget()
    plot.setBackground(PANEL_BG)
    plot.showGrid(x=False, y=True, alpha=0.15)
    plot.setYRange(0, y_max, padding=0.05)
    plot.setXRange(0, HISTORY_LEN, padding=0)
    plot.getAxis("left").setTextPen(pg.mkColor(TEXT_DIM))
    plot.getAxis("bottom").setStyle(showValues=False)
    plot.getAxis("bottom").setPen(pg.mkColor(PANEL_BORDER))
    plot.getAxis("left").setPen(pg.mkColor(PANEL_BORDER))
    plot.setMouseEnabled(x=False, y=False)
    plot.hideButtons()
    plot.setMenuEnabled(False)

    color = pg.mkColor(fill_color)
    fill = pg.mkColor(fill_color)
    fill.setAlpha(45)
    pen = pg.mkPen(color=color, width=2)
    curve = plot.plot([], [], pen=pen, fillLevel=0, brush=fill)
    plot.setFixedHeight(90)
    return plot, curve


def fmt_bytes(n: float) -> str:
    for unit in ("B", "K", "M", "G", "T"):
        if abs(n) < 1024.0:
            return f"{n:5.1f}{unit}"
        n /= 1024.0
    return f"{n:5.1f}P"


def fmt_rate(bps: float) -> str:
    return f"{fmt_bytes(bps)}/s"


def fmt_uptime(boot_ts) -> str:
    if not boot_ts:
        return "--"
    secs = int(time.time() - boot_ts)
    d, rem = divmod(secs, 86400)
    h, rem = divmod(rem, 3600)
    m, _ = divmod(rem, 60)
    if d:
        return f"{d}d {h:02d}h {m:02d}m"
    return f"{h:02d}h {m:02d}m"


# ----------------------------------------------------------------------
# Core panels
# ----------------------------------------------------------------------

class HeaderBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 8, 18, 8)

        title = QLabel("SYSPULSE")
        title.setStyleSheet(f"""
            color: {GREEN};
            font-family: '{FONT_FAMILY}';
            font-size: 20px;
            font-weight: 700;
            letter-spacing: 6px;
        """)
        subtitle = QLabel("REAL-TIME SYSTEM TELEMETRY")
        subtitle.setStyleSheet(f"""
            color: {TEXT_FAINT};
            font-family: '{FONT_FAMILY}';
            font-size: 10px;
            letter-spacing: 3px;
        """)
        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        title_wrap = QWidget()
        title_wrap.setLayout(title_box)

        self.host_lbl = QLabel(platform.node() or "localhost")
        self.host_lbl.setStyleSheet(
            f"color:{TEXT_DIM}; font-family:'{FONT_FAMILY}'; font-size:11px;"
        )
        self.os_lbl = QLabel(f"{platform.system()} {platform.release()}")
        self.os_lbl.setStyleSheet(
            f"color:{TEXT_FAINT}; font-family:'{FONT_FAMILY}'; font-size:10px;"
        )
        info_box = QVBoxLayout()
        info_box.setSpacing(0)
        info_box.addWidget(self.host_lbl, alignment=Qt.AlignmentFlag.AlignRight)
        info_box.addWidget(self.os_lbl, alignment=Qt.AlignmentFlag.AlignRight)
        info_wrap = QWidget()
        info_wrap.setLayout(info_box)

        self.clock_lbl = QLabel("00:00:00")
        self.clock_lbl.setStyleSheet(f"""
            color: {GREEN};
            font-family: '{FONT_FAMILY}';
            font-size: 18px;
            font-weight: 600;
        """)

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(f"color:{GREEN}; font-size: 14px;")

        layout.addWidget(title_wrap)
        layout.addStretch(1)
        layout.addWidget(info_wrap)
        layout.addSpacing(20)
        layout.addWidget(self.status_dot)
        layout.addWidget(self.clock_lbl)

        self.setStyleSheet(f"background-color: {BG}; border-bottom: 1px solid {PANEL_BORDER};")

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick)
        self._clock_timer.start(1000)
        self._tick()

    def _tick(self):
        self.clock_lbl.setText(datetime.now().strftime("%H:%M:%S"))


class CpuPanel(Panel):
    def __init__(self, core_count: int, parent=None):
        super().__init__("CPU LOAD", parent)

        self.total_bar = MetricBar("TOTAL")
        self.body_layout.addWidget(self.total_bar)

        self.plot, self.curve = make_plot(y_max=100, fill_color=GREEN)
        self.body_layout.addWidget(self.plot)
        self.history = deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN)

        self.freq_row = StatRow("FREQ", "--")
        self.body_layout.addWidget(self.freq_row)

        # Per-core grid
        self.core_bars: list[QProgressBar] = []
        core_grid = QGridLayout()
        core_grid.setSpacing(4)
        cols = 4
        for i in range(core_count):
            lbl = QLabel(f"C{i}")
            lbl.setStyleSheet(
                f"color:{TEXT_FAINT}; font-family:'{FONT_FAMILY}'; font-size:9px;"
            )
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setTextVisible(False)
            bar.setFixedHeight(6)
            bar.setStyleSheet(f"""
                QProgressBar {{ background-color:{BG}; border:1px solid {PANEL_BORDER}; }}
                QProgressBar::chunk {{ background-color:{GREEN_DIM}; }}
            """)
            r, c = divmod(i, cols)
            core_grid.addWidget(lbl, r * 2, c)
            core_grid.addWidget(bar, r * 2 + 1, c)
            self.core_bars.append(bar)
        core_wrap = QWidget()
        core_wrap.setLayout(core_grid)
        self.body_layout.addWidget(core_wrap)

    def update_data(self, data: dict):
        self.total_bar.set_value(data["cpu_total"])
        self.history.append(data["cpu_total"])
        self.curve.setData(list(range(len(self.history))), list(self.history))

        freq = data.get("cpu_freq")
        if freq:
            self.freq_row.set_value(f"{freq.current/1000:.2f} GHz")
        else:
            self.freq_row.set_value("N/A")

        for i, pct in enumerate(data["cpu_per_core"]):
            if i >= len(self.core_bars):
                break
            bar = self.core_bars[i]
            bar.setValue(int(pct))
            color = level_color(pct)
            bar.setStyleSheet(f"""
                QProgressBar {{ background-color:{BG}; border:1px solid {PANEL_BORDER}; }}
                QProgressBar::chunk {{ background-color:{color}; }}
            """)


class MemoryPanel(Panel):
    def __init__(self, parent=None):
        super().__init__("MEMORY", parent)

        self.ram_bar = MetricBar("RAM")
        self.body_layout.addWidget(self.ram_bar)

        self.plot, self.curve = make_plot(y_max=100, fill_color=CYAN)
        self.body_layout.addWidget(self.plot)
        self.history = deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN)

        self.used_row = StatRow("USED", "--")
        self.avail_row = StatRow("AVAILABLE", "--")
        self.body_layout.addWidget(self.used_row)
        self.body_layout.addWidget(self.avail_row)

        self.swap_bar = MetricBar("SWAP")
        self.body_layout.addWidget(self.swap_bar)

    def update_data(self, data: dict):
        self.ram_bar.set_value(data["mem_percent"])
        self.history.append(data["mem_percent"])
        self.curve.setData(list(range(len(self.history))), list(self.history))

        self.used_row.set_value(f"{fmt_bytes(data['mem_used'])} / {fmt_bytes(data['mem_total'])}")
        self.avail_row.set_value(fmt_bytes(data["mem_available"]))
        self.swap_bar.set_value(data["swap_percent"])


class NetworkPanel(Panel):
    def __init__(self, parent=None):
        super().__init__("NETWORK", parent)

        row = QHBoxLayout()
        self.up_row = StatRow("↑ UP", "0 B/s")
        self.down_row = StatRow("↓ DOWN", "0 B/s")
        col1 = QVBoxLayout()
        col1.addWidget(self.up_row)
        col1.addWidget(self.down_row)
        row_wrap = QWidget()
        row_wrap.setLayout(col1)
        self.body_layout.addWidget(row_wrap)

        self.plot, self.curve_down = make_plot(y_max=100, fill_color=CYAN)
        pen_up = pg.mkPen(color=pg.mkColor(AMBER), width=2)
        fill_up = pg.mkColor(AMBER)
        fill_up.setAlpha(35)
        self.curve_up = self.plot.plot([], [], pen=pen_up, fillLevel=0, brush=fill_up)
        self.body_layout.addWidget(self.plot)

        self.down_history = deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN)
        self.up_history = deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN)
        self._ymax = 100.0

        self.total_row = StatRow("TOTAL TX/RX", "--")
        self.body_layout.addWidget(self.total_row)

    def update_data(self, data: dict):
        self.up_row.set_value(fmt_rate(data["net_up"]), color=AMBER)
        self.down_row.set_value(fmt_rate(data["net_down"]), color=CYAN)

        down_kb = data["net_down"] / 1024.0
        up_kb = data["net_up"] / 1024.0
        self.down_history.append(down_kb)
        self.up_history.append(up_kb)

        peak = max(max(self.down_history), max(self.up_history), 10.0)
        self._ymax = max(peak * 1.2, 10.0)
        self.plot.setYRange(0, self._ymax, padding=0)

        xs = list(range(len(self.down_history)))
        self.curve_down.setData(xs, list(self.down_history))
        self.curve_up.setData(xs, list(self.up_history))

        self.total_row.set_value(
            f"{fmt_bytes(data['net_up_total'])} / {fmt_bytes(data['net_down_total'])}"
        )


class DiskPanel(Panel):
    def __init__(self, parent=None):
        super().__init__("DISK", parent)
        self.bars: dict[str, MetricBar] = {}
        self._container = QVBoxLayout()
        self._container.setSpacing(8)
        wrap = QWidget()
        wrap.setLayout(self._container)
        self.body_layout.addWidget(wrap)
        self.body_layout.addStretch(1)

    def update_data(self, data: dict):
        usage = data.get("disk_usage", {})
        for mount, u in usage.items():
            if mount not in self.bars:
                label = mount if len(mount) <= 10 else mount[:9] + "…"
                bar = MetricBar(label)
                self.bars[mount] = bar
                self._container.addWidget(bar)
            self.bars[mount].set_value(u.percent)


class TempPanel(Panel):
    def __init__(self, parent=None):
        super().__init__("THERMAL", parent)
        self.rows: dict[str, StatRow] = {}
        self._container = QVBoxLayout()
        self._container.setSpacing(6)
        wrap = QWidget()
        wrap.setLayout(self._container)
        self.body_layout.addWidget(wrap)
        self._placeholder = QLabel("NO SENSOR DATA")
        self._placeholder.setStyleSheet(
            f"color:{TEXT_FAINT}; font-family:'{FONT_FAMILY}'; font-size:10px;"
        )
        self._container.addWidget(self._placeholder)
        self.body_layout.addStretch(1)

    def update_data(self, data: dict):
        temps = data.get("temps") or {}
        if not temps:
            return
        self._placeholder.setVisible(False)
        for name, entries in temps.items():
            for entry in entries:
                key = f"{name}:{entry.label or 'core'}"
                if key not in self.rows:
                    row = StatRow(key[:18].upper(), "--")
                    self.rows[key] = row
                    self._container.addWidget(row)
                color = level_color(min(entry.current, 100))
                self.rows[key].set_value(f"{entry.current:.1f}°C", color=color)


class ProcessPanel(Panel):
    def __init__(self, parent=None):
        super().__init__("TOP PROCESSES", parent)
        self.uptime_row = StatRow("UPTIME", "--")
        self.procs_row = StatRow("PROCESSES", "--")
        self.body_layout.addWidget(self.uptime_row)
        self.body_layout.addWidget(self.procs_row)

        header = QHBoxLayout()
        for text, w in (("PID", 50), ("NAME", 130), ("CPU%", 55), ("MEM%", 55)):
            lbl = QLabel(text)
            lbl.setFixedWidth(w)
            lbl.setStyleSheet(
                f"color:{TEXT_FAINT}; font-family:'{FONT_FAMILY}'; font-size:9px; letter-spacing:1px;"
            )
            header.addWidget(lbl)
        header_wrap = QWidget()
        header_wrap.setLayout(header)
        self.body_layout.addWidget(header_wrap)

        self.rows_container = QVBoxLayout()
        self.rows_container.setSpacing(3)
        rows_wrap = QWidget()
        rows_wrap.setLayout(self.rows_container)
        self.body_layout.addWidget(rows_wrap)
        self._row_widgets: list[list[QLabel]] = []

    def update_data(self, data: dict):
        self.uptime_row.set_value(fmt_uptime(data.get("boot_ts")))
        self.procs_row.set_value(str(data.get("proc_count", "--")))

        procs = data.get("top_procs", [])
        while len(self._row_widgets) < len(procs):
            row = QHBoxLayout()
            labels = []
            for w in (50, 130, 55, 55):
                lbl = QLabel("")
                lbl.setFixedWidth(w)
                lbl.setStyleSheet(
                    f"color:{TEXT_DIM}; font-family:'{FONT_FAMILY}'; font-size:10px;"
                )
                row.addWidget(lbl)
                labels.append(lbl)
            row_wrap = QWidget()
            row_wrap.setLayout(row)
            self.rows_container.addWidget(row_wrap)
            self._row_widgets.append(labels)

        for i, labels in enumerate(self._row_widgets):
            if i < len(procs):
                p = procs[i]
                cpu = p.get("cpu_percent") or 0.0
                mem = p.get("memory_percent") or 0.0
                labels[0].setText(str(p.get("pid", "")))
                labels[1].setText((p.get("name") or "?")[:18])
                labels[2].setText(f"{cpu:.1f}")
                labels[2].setStyleSheet(
                    f"color:{level_color(cpu)}; font-family:'{FONT_FAMILY}'; font-size:10px;"
                )
                labels[3].setText(f"{mem:.1f}")
                for lbl in (labels[0], labels[1]):
                    lbl.setVisible(True)
                labels[1].setVisible(True)
            else:
                for lbl in labels:
                    lbl.setText("")


# ----------------------------------------------------------------------
# Main window
# ----------------------------------------------------------------------

class SysPulseWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SysPulse — System Telemetry")
        self.resize(1180, 800)
        self.setStyleSheet(f"background-color: {BG};")

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.header = HeaderBar()
        root.addWidget(self.header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {BG}; }}")
        root.addWidget(scroll, 1)

        content = QWidget()
        content.setStyleSheet(f"background-color: {BG};")
        scroll.setWidget(content)

        grid = QGridLayout(content)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setSpacing(14)

        core_count = psutil.cpu_count(logical=True) or 4
        self.cpu_panel = CpuPanel(core_count)
        self.mem_panel = MemoryPanel()
        self.net_panel = NetworkPanel()
        self.disk_panel = DiskPanel()
        self.temp_panel = TempPanel()
        self.proc_panel = ProcessPanel()

        grid.addWidget(self.cpu_panel, 0, 0, 2, 1)
        grid.addWidget(self.mem_panel, 0, 1)
        grid.addWidget(self.net_panel, 1, 1)
        grid.addWidget(self.disk_panel, 0, 2)
        grid.addWidget(self.temp_panel, 1, 2)
        grid.addWidget(self.proc_panel, 2, 0, 1, 3)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        # Background sampling thread
        self.sampler_thread = QThread()
        self.sampler = SystemSampler(interval_ms=1000)
        self.sampler.moveToThread(self.sampler_thread)
        self.sampler_thread.started.connect(self.sampler.run)
        self.sampler.sample_ready.connect(self.on_sample)
        self.sampler_thread.start()

    def on_sample(self, data: dict):
        self.cpu_panel.update_data(data)
        self.mem_panel.update_data(data)
        self.net_panel.update_data(data)
        self.disk_panel.update_data(data)
        self.temp_panel.update_data(data)
        self.proc_panel.update_data(data)

        max_load = max(data["cpu_total"], data["mem_percent"])
        self.header.status_dot.setStyleSheet(f"color:{level_color(max_load)}; font-size:14px;")

    def closeEvent(self, event):
        self.sampler.stop()
        self.sampler_thread.quit()
        self.sampler_thread.wait(2000)
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    font_family = load_mono_font()
    app.setFont(QFont(font_family, 10))

    win = SysPulseWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
