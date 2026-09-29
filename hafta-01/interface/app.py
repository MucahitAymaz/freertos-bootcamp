"""FreeRTOS Bootcamp - week 1 telemetry and response-time interface.

The interface only observes: it reads lines from the board, sends the
SCN/STOP/DUMP commands and saves DUMP output verbatim. It never changes
or generates measurement data.

Run:  python app.py
"""
from __future__ import annotations

import csv
import queue
import time
import tkinter as tk
from collections import deque
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

import plots
from protocol import (Ack, Btn, Counters, DumpCollector, DumpResult, Err, EventRow,
                      MSG_LEN, Tel, Unknown, load_event_csv, parse_line)
from serial_link import SerialLink, list_ports

HERE = Path(__file__).resolve().parent
MEAS_DIR = HERE.parent / "measurements"
LOG_DIR = HERE / "logs"

SCENARIOS = [
    ("S0", "Telemetri kapalı · referans"),
    ("S1", "10 Hz · 100 ms"),
    ("S2", "50 Hz · 20 ms"),
    ("S3", "100 Hz · 10 ms"),
    ("S4", "100 Hz + ≈2 ms CPU"),
    ("S5", "100 Hz + ≈5 ms CPU"),
]
WARMUP_S = 5.0
TARGET_PRESSES = 30
MIN_PRESS_GAP_S = 0.5
LIVE_WINDOW_S = 60.0
MAX_LOG_LINES = 600


class Chart:
    """A matplotlib figure embedded in a Tk frame with the zoom/save toolbar."""

    def __init__(self, parent) -> None:
        self.fig = Figure(figsize=(8, 4.5), dpi=100, layout="constrained")
        self.ax = self.fig.add_subplot(111)
        plots.apply_style(self.fig)
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        toolbar = NavigationToolbar2Tk(self.canvas, parent, pack_toolbar=False)
        toolbar.update()
        toolbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def draw(self) -> None:
        self.canvas.draw_idle()


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("FreeRTOS Bootcamp · Hafta 1 · Yanıt Süresi Ölçüm Arayüzü")
        self.geometry("1440x900")
        self.minsize(1100, 720)

        self.rxq: queue.Queue = queue.Queue()
        self.link = SerialLink(self.rxq)
        self.dump = DumpCollector()
        self.last_dump: DumpResult | None = None
        self.session_log = None

        # Live state (PC-side, used only for display)
        self.tel_count = 0
        self.tel_gaps = 0
        self.tel_bad_len = 0
        self.last_tel_seq = None
        self.tel_times: deque = deque()
        self.rate_hist: deque = deque(maxlen=int(LIVE_WINDOW_S) + 5)
        self.btn_marks: deque = deque(maxlen=200)
        self.btn_count = 0
        self.last_btn_pc = None
        self.fast_presses = 0
        self.scn_started_pc = None
        self.active_scn = None

        self._build_style()
        self._build_ui()
        self._refresh_ports()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(50, self._poll_rx)
        self.after(1000, self._tick_1s)

    # ------------------------------------------------------------------ UI
    def _build_style(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        base = ("Segoe UI", 10)
        style.configure(".", font=base)
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 12))
        style.configure("Big.TLabel", font=("Segoe UI Semibold", 20))
        style.configure("Muted.TLabel", foreground="#666666")
        style.configure("Scn.TButton", font=("Segoe UI Semibold", 10), padding=(6, 6))
        style.configure("Accent.TButton", font=("Segoe UI Semibold", 10), padding=(6, 6))

    def _build_ui(self) -> None:
        # Top bar: connection
        top = ttk.Frame(self, padding=(10, 8))
        top.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(top, text="Port:").pack(side=tk.LEFT)
        self.port_var = tk.StringVar()
        self.port_box = ttk.Combobox(top, textvariable=self.port_var, width=48, state="readonly")
        self.port_box.pack(side=tk.LEFT, padx=(4, 4))
        ttk.Button(top, text="↻", width=3, command=self._refresh_ports).pack(side=tk.LEFT)
        self.conn_btn = ttk.Button(top, text="Bağlan", style="Accent.TButton",
                                   command=self._toggle_connect)
        self.conn_btn.pack(side=tk.LEFT, padx=(8, 16))
        self.log_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Ham oturum kaydı (interface/logs)",
                        variable=self.log_var).pack(side=tk.LEFT)
        self.status_var = tk.StringVar(value="Bağlı değil")
        ttk.Label(top, textvariable=self.status_var, style="Muted.TLabel").pack(side=tk.RIGHT)

        body = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        left = ttk.Frame(body, padding=(6, 4))
        right = ttk.Frame(body)
        body.add(left, weight=0)
        body.add(right, weight=1)

        self._build_left(left)
        self._build_tabs(right)

    def _build_left(self, left) -> None:
        # Scenario control
        box = ttk.LabelFrame(left, text=" Senaryo ", padding=8)
        box.pack(fill=tk.X)
        for i, (scn, desc) in enumerate(SCENARIOS):
            b = ttk.Button(box, text=f"{scn}", style="Scn.TButton", width=5,
                           command=lambda s=scn: self._send_scn(s))
            b.grid(row=i, column=0, sticky="w", pady=2)
            ttk.Label(box, text=desc).grid(row=i, column=1, sticky="w", padx=8)
        row = ttk.Frame(box)
        row.grid(row=len(SCENARIOS), column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(row, text="STOP", command=lambda: self._send("STOP")).pack(side=tk.LEFT)
        ttk.Button(row, text="DUMP", command=lambda: self._send("DUMP")).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="STOP + DUMP", style="Accent.TButton",
                   command=self._stop_and_dump).pack(side=tk.LEFT)
        self.autosave_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(box, text="DUMP gelince measurements/Sx.csv olarak kaydet",
                        variable=self.autosave_var).grid(row=len(SCENARIOS) + 1, column=0,
                                                         columnspan=2, sticky="w", pady=(6, 0))

        # Measurement procedure helper
        proc = ttk.LabelFrame(left, text=" Ölçüm prosedürü ", padding=8)
        proc.pack(fill=tk.X, pady=(8, 0))
        self.scn_var = tk.StringVar(value="Aktif senaryo: —")
        ttk.Label(proc, textvariable=self.scn_var, style="Title.TLabel").pack(anchor="w")
        self.warm_var = tk.StringVar(value="Isınma: —")
        self.warm_lbl = ttk.Label(proc, textvariable=self.warm_var)
        self.warm_lbl.pack(anchor="w", pady=(2, 0))
        self.press_var = tk.StringVar(value=f"Basış: 0 / {TARGET_PRESSES}")
        ttk.Label(proc, textvariable=self.press_var).pack(anchor="w", pady=(6, 0))
        self.press_bar = ttk.Progressbar(proc, maximum=TARGET_PRESSES, length=260)
        self.press_bar.pack(fill=tk.X, pady=(2, 0))
        self.gap_var = tk.StringVar(value="")
        ttk.Label(proc, textvariable=self.gap_var, foreground="#C0392B").pack(anchor="w", pady=(4, 0))

        # Button event banner
        ev = ttk.LabelFrame(left, text=" Son buton olayı ", padding=8)
        ev.pack(fill=tk.X, pady=(8, 0))
        self.event_var = tk.StringVar(value="—")
        self.event_lbl = tk.Label(ev, textvariable=self.event_var, font=("Segoe UI Semibold", 18),
                                  bg="#F1F3F5", fg="#333333", pady=10)
        self.event_lbl.pack(fill=tk.X)

        # Live link statistics
        st = ttk.LabelFrame(left, text=" Canlı istatistik (PC tarafı) ", padding=8)
        st.pack(fill=tk.X, pady=(8, 0))
        self.stat_vars = {}
        for key, label in (("rate", "TEL hızı"), ("tel", "TEL satırı"), ("gaps", "TEL sıra boşluğu"),
                           ("len", "64 bayt dışı satır"), ("btn", "BTN satırı")):
            f = ttk.Frame(st)
            f.pack(fill=tk.X)
            ttk.Label(f, text=label).pack(side=tk.LEFT)
            v = tk.StringVar(value="0")
            ttk.Label(f, textvariable=v, style="Title.TLabel").pack(side=tk.RIGHT)
            self.stat_vars[key] = v

        # Counters from the last DUMP
        cnt = ttk.LabelFrame(left, text=" Son DUMP sayaçları (kart) ", padding=6)
        cnt.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self.cnt_tree = ttk.Treeview(cnt, columns=("v",), show="tree headings", height=12)
        self.cnt_tree.heading("#0", text="sayaç")
        self.cnt_tree.heading("v", text="değer")
        self.cnt_tree.column("#0", width=170)
        self.cnt_tree.column("v", width=90, anchor="e")
        self.cnt_tree.tag_configure("warn", foreground="#C0392B")
        self.cnt_tree.pack(fill=tk.BOTH, expand=True)

    def _build_tabs(self, right) -> None:
        nb = ttk.Notebook(right)
        nb.pack(fill=tk.BOTH, expand=True)
        self.charts = {}

        live = ttk.Frame(nb)
        nb.add(live, text="  Canlı  ")
        pane = ttk.Panedwindow(live, orient=tk.VERTICAL)
        pane.pack(fill=tk.BOTH, expand=True)
        chart_frame = ttk.Frame(pane)
        log_frame = ttk.Frame(pane)
        pane.add(chart_frame, weight=3)
        pane.add(log_frame, weight=2)
        self.charts["live"] = Chart(chart_frame)
        self.log_text = tk.Text(log_frame, height=10, font=("Consolas", 9), bg="#1E1E1E",
                                fg="#BDBDBD", insertbackground="white", wrap="none")
        sb = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        for tag, color in (("TEL", "#7A7A7A"), ("BTN", "#4ADE80"), ("ACK", "#60A5FA"),
                           ("ERR", "#F87171"), ("DUMP", "#FBBF24"), ("TX", "#C084FC")):
            self.log_text.tag_configure(tag, foreground=color)
        cmd = ttk.Frame(log_frame)
        cmd.pack(fill=tk.X, before=self.log_text)
        ttk.Label(cmd, text="Komut:").pack(side=tk.LEFT, padx=(4, 4))
        self.cmd_var = tk.StringVar()
        entry = ttk.Entry(cmd, textvariable=self.cmd_var, width=30)
        entry.pack(side=tk.LEFT)
        entry.bind("<Return>", lambda _e: self._send_custom())
        ttk.Button(cmd, text="Gönder", command=self._send_custom).pack(side=tk.LEFT, padx=4)
        self.show_tel_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(cmd, text="TEL satırlarını göster", variable=self.show_tel_var).pack(side=tk.LEFT, padx=12)

        for key, text in (("r", "  Yanıt süresi R  "), ("stages", "  Aşamalar  "),
                          ("dist", "  Dağılım  "), ("compare", "  Senaryo karşılaştırma  ")):
            frame = ttk.Frame(nb)
            nb.add(frame, text=text)
            if key == "compare":
                bar = ttk.Frame(frame, padding=4)
                bar.pack(side=tk.TOP, fill=tk.X)
                ttk.Button(bar, text="measurements/ klasöründen yenile",
                           command=self._refresh_compare).pack(side=tk.LEFT)
                self.compare_info = tk.StringVar(value="")
                ttk.Label(bar, textvariable=self.compare_info, style="Muted.TLabel").pack(side=tk.LEFT, padx=10)
            self.charts[key] = Chart(frame)

        self._redraw_dump_charts([])
        self._refresh_compare()

    # ------------------------------------------------------------ actions
    def _refresh_ports(self) -> None:
        ports = list_ports()
        values = [f"{dev} — {desc}" for dev, desc in ports]
        self.port_box["values"] = values
        if values and not self.port_var.get():
            self.port_var.set(values[0])

    def _toggle_connect(self) -> None:
        if self.link.is_open:
            self._disconnect()
            return
        sel = self.port_var.get()
        if not sel:
            messagebox.showwarning("Port", "Önce bir port seç.")
            return
        port = sel.split(" — ")[0]
        try:
            self.link.open(port)
        except Exception as exc:  # noqa: BLE001 - show any open error to the user
            messagebox.showerror("Bağlantı hatası",
                                 f"{port} açılamadı:\n{exc}\n\nTera Term gibi başka bir program portu kullanıyor olabilir.")
            return
        if self.log_var.get():
            LOG_DIR.mkdir(exist_ok=True)
            name = LOG_DIR / f"session_{datetime.now():%Y%m%d_%H%M%S}.log"
            self.session_log = open(name, "w", encoding="ascii", errors="replace", newline="\n")
        self.conn_btn.configure(text="Bağlantıyı kes")
        self.status_var.set(f"Bağlı: {port} · 115200 8N1")
        self._log(f"# bağlandı: {port}", "ACK")

    def _disconnect(self) -> None:
        self.link.close()
        if self.session_log:
            self.session_log.close()
            self.session_log = None
        self.conn_btn.configure(text="Bağlan")
        self.status_var.set("Bağlı değil")

    def _send(self, text: str) -> None:
        try:
            self.link.send_line(text)
        except Exception as exc:  # noqa: BLE001
            messagebox.showwarning("Gönderilemedi", str(exc))
            return
        self._log(f">> {text}", "TX")
        if self.session_log:
            self.session_log.write(f">> {text}\n")

    def _send_custom(self) -> None:
        text = self.cmd_var.get().strip()
        if text:
            self._send(text)
            self.cmd_var.set("")

    def _send_scn(self, scn: str) -> None:
        self._send(f"SCN,{scn}")

    def _stop_and_dump(self) -> None:
        self._send("STOP")
        # Queued TEL frames drain first (FIFO on the board); DUMP is queued behind them
        self.after(300, lambda: self._send("DUMP"))

    def _reset_scenario_view(self, scn: str) -> None:
        self.active_scn = scn
        self.scn_started_pc = time.monotonic()
        self.btn_count = 0
        self.fast_presses = 0
        self.last_btn_pc = None
        self.last_tel_seq = None
        self.tel_gaps = 0
        self.tel_bad_len = 0
        self.btn_marks.clear()
        self.scn_var.set(f"Aktif senaryo: {scn}")
        self.press_bar["value"] = 0
        self.press_var.set(f"Basış: 0 / {TARGET_PRESSES}")
        self.gap_var.set("")
        self.event_var.set("—")
        self.event_lbl.configure(bg="#F1F3F5", fg="#333333")

    # ---------------------------------------------------------- rx handling
    def _poll_rx(self) -> None:
        batch = 0
        try:
            while batch < 400:
                line, err, t_pc = self.rxq.get_nowait()
                batch += 1
                if line == SerialLink.ERROR:
                    self._log(f"# seri port hatası: {err}", "ERR")
                    self._disconnect()
                    break
                self._handle_line(line, t_pc)
        except queue.Empty:
            pass
        self.after(50, self._poll_rx)

    def _handle_line(self, line: str, t_pc: float) -> None:
        if self.session_log:
            self.session_log.write(line + "\n")
        msg = parse_line(line)
        done = self.dump.feed(msg)

        if isinstance(msg, Tel):
            self.tel_count += 1
            self.tel_times.append(t_pc)
            if msg.length != MSG_LEN:
                self.tel_bad_len += 1
            if self.last_tel_seq is not None and msg.seq != self.last_tel_seq + 1:
                self.tel_gaps += 1
            self.last_tel_seq = msg.seq
            if self.show_tel_var.get():
                self._log(line.rstrip(), "TEL")
        elif isinstance(msg, Btn):
            self._on_btn(msg, t_pc, line)
        elif isinstance(msg, Ack):
            self._log(line, "ACK")
            if msg.text.startswith("SCN,"):
                self._reset_scenario_view(msg.text.split(",")[1])
            elif msg.text == "STOP":
                self.warm_var.set("Telemetri durduruldu → DUMP")
        elif isinstance(msg, Err):
            self._log(line, "ERR")
            self.status_var.set(f"Kart hatası: {msg.text}")
        elif isinstance(msg, (EventRow, Counters)) or self.dump.active or done is not None:
            self._log(line, "DUMP")
        elif isinstance(msg, Unknown) and msg.raw:
            self._log(line, None)

        if done is not None:
            self._on_dump(done)

    def _on_btn(self, msg: Btn, t_pc: float, line: str) -> None:
        self.btn_count += 1
        if msg.length != MSG_LEN:
            self.tel_bad_len += 1
        if self.last_btn_pc is not None and (t_pc - self.last_btn_pc) < MIN_PRESS_GAP_S:
            self.fast_presses += 1
            self.gap_var.set(f"⚠ {self.fast_presses} basış 0,5 s'den kısa aralıklı (PC saatine göre)")
        self.last_btn_pc = t_pc
        self.btn_marks.append((t_pc, msg.event_id))
        self.event_var.set(f"Butona basıldı · Olay {msg.event_id}")
        self.event_lbl.configure(bg="#D1FAE5", fg="#065F46")
        self.after(400, lambda: self.event_lbl.configure(bg="#F1F3F5", fg="#333333"))
        self.press_bar["value"] = min(self.btn_count, TARGET_PRESSES)
        self.press_var.set(f"Basış: {self.btn_count} / {TARGET_PRESSES}"
                           + ("  ✔" if self.btn_count >= TARGET_PRESSES else ""))
        self._log(line.rstrip(), "BTN")

    def _on_dump(self, res: DumpResult) -> None:
        self.last_dump = res
        self._show_counters(res.counters)
        scn = res.scenario or self.active_scn or "S?"
        self._redraw_dump_charts(res.rows, scn)
        self._log(f"# DUMP tamam: {len(res.rows)} olay ({scn})", "ACK")
        if self.autosave_var.get():
            self._save_dump(res, scn)

    def _save_dump(self, res: DumpResult, scn: str) -> None:
        MEAS_DIR.mkdir(exist_ok=True)
        path = MEAS_DIR / f"{scn}.csv"
        if path.exists():
            if not messagebox.askyesno("Dosya var",
                                       f"{path.name} zaten var. Üzerine yazılsın mı?\n"
                                       "Hayır dersen kayıt yapılmaz."):
                self._log(f"# {path.name} kaydedilmedi (kullanıcı iptal etti)", "ERR")
                return
        # Verbatim board output: header + event rows, never edited
        with open(path, "w", encoding="ascii", newline="\n") as f:
            f.write(res.header + "\n")
            for r in res.rows:
                f.write(r.raw + "\n")
        if res.counters is not None:
            with open(MEAS_DIR / f"{scn}_counters.csv", "w", encoding="ascii", newline="") as f:
                w = csv.writer(f, lineterminator="\n")
                w.writerow(["counter", "value"])
                for k, v in res.counters.values.items():
                    w.writerow([k, v])
        self._log(f"# kaydedildi: measurements/{path.name} ({len(res.rows)} olay)", "ACK")
        self.status_var.set(f"Kaydedildi: measurements/{path.name}")
        self._refresh_compare()

    def _show_counters(self, counters) -> None:
        self.cnt_tree.delete(*self.cnt_tree.get_children())
        if counters is None:
            return
        watch = {"btn_drop", "tx_drop_tel", "tx_drop_btn", "tx_error", "timeout",
                 "log_overflow", "fmt_error", "cmd_drop", "rx_error"}
        for k, v in counters.values.items():
            warn = k in watch and v not in ("", "0")
            self.cnt_tree.insert("", tk.END, text=k, values=(v if v != "" else "—",),
                                 tags=("warn",) if warn else ())

    # --------------------------------------------------------------- charts
    def _redraw_dump_charts(self, rows, scn: str = "") -> None:
        suffix = f"· {scn}" if scn else ""
        plots.plot_r(self.charts["r"].ax, rows, suffix)
        plots.plot_stages(self.charts["stages"].ax, rows)
        plots.plot_distribution(self.charts["dist"].ax, rows)
        for key in ("r", "stages", "dist"):
            self.charts[key].draw()

    def _refresh_compare(self) -> None:
        data, skipped = {}, []
        for path in sorted(MEAS_DIR.glob("S[0-9].csv")):
            try:
                data[path.stem] = load_event_csv(path)
            except (OSError, ValueError) as exc:
                skipped.append(f"{path.name}: {exc}")
        plots.plot_compare(self.charts["compare"].ax, data)
        self.charts["compare"].draw()
        info = f"Yüklenen: {', '.join(sorted(data)) or 'yok'}"
        if skipped:
            info += f" · atlanan: {'; '.join(skipped)}"
        self.compare_info.set(info)

    def _tick_1s(self) -> None:
        now = time.monotonic()
        while self.tel_times and now - self.tel_times[0] > 1.0:
            self.tel_times.popleft()
        rate = len(self.tel_times)
        self.rate_hist.append((now, rate))
        self.stat_vars["rate"].set(f"{rate} /s")
        self.stat_vars["tel"].set(str(self.tel_count))
        self.stat_vars["gaps"].set(str(self.tel_gaps))
        self.stat_vars["len"].set(str(self.tel_bad_len))
        self.stat_vars["btn"].set(str(self.btn_count))

        if self.scn_started_pc is not None and self.active_scn:
            el = now - self.scn_started_pc
            if el < WARMUP_S:
                self.warm_var.set(f"Isınma: {el:4.1f} / {WARMUP_S:.0f} s · henüz basma")
                self.warm_lbl.configure(foreground="#B45309")
            elif not self.warm_var.get().startswith("Telemetri durduruldu"):
                self.warm_var.set(f"Isınma tamam ✔ · {el:5.0f} s geçti · basışlara başla")
                self.warm_lbl.configure(foreground="#15803D")

        plots.plot_live(self.charts["live"].ax, list(self.rate_hist), list(self.btn_marks), LIVE_WINDOW_S)
        self.charts["live"].draw()
        self.after(1000, self._tick_1s)

    # ------------------------------------------------------------------ log
    def _log(self, text: str, tag) -> None:
        self.log_text.insert(tk.END, text + "\n", (tag,) if tag else ())
        lines = int(self.log_text.index("end-1c").split(".")[0])
        if lines > MAX_LOG_LINES:
            self.log_text.delete("1.0", f"{lines - MAX_LOG_LINES}.0")
        self.log_text.see(tk.END)

    def _on_close(self) -> None:
        self._disconnect()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
