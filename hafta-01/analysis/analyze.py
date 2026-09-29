"""Week-1 analysis: measurements/S0..S5.csv -> summary.csv, two plots, report tables.

Every number in analysis/report.md must come from this script's output.
Raw CSV files are only read, never modified.

Run:  python hafta-01/analysis/analyze.py
"""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path
from statistics import mean, median

import matplotlib

matplotlib.use("Agg")  # file output only, no window
from matplotlib.figure import Figure  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "interface"))  # reuse protocol + plots from the GUI

import plots  # noqa: E402
from protocol import load_event_csv  # noqa: E402

MEAS = ROOT / "measurements"
PLOTS = HERE / "plots"
SCENARIOS = ["S0", "S1", "S2", "S3", "S4", "S5"]
SCN_DESC = {
    "S0": "kapalı, iş yok",
    "S1": "100 ms, iş yok",
    "S2": "20 ms, iş yok",
    "S3": "10 ms, iş yok",
    "S4": "10 ms, ≈2 ms iş",
    "S5": "10 ms, ≈5 ms iş",
}
DEADLINE_US = 20_000
MIN_PRESS_GAP_S = 0.5


def p95(values: list) -> float:
    """Nearest-rank 95th percentile (no interpolation, value is an observed sample)."""
    s = sorted(values)
    return s[max(0, math.ceil(0.95 * len(s)) - 1)]


def load_counters(scn: str) -> dict:
    path = MEAS / f"{scn}_counters.csv"
    if not path.exists():
        return {}
    with open(path, newline="", encoding="ascii") as f:
        return {row["counter"]: row["value"] for row in csv.DictReader(f)}


def ms(us: float) -> float:
    return us / 1000.0


def tel_rate(cnt: dict) -> str:
    """Measured telemetry rate from the board's min/max period counters ("" when off)."""
    lo, hi = cnt.get("tel_period_min_us", ""), cnt.get("tel_period_max_us", "")
    if not lo or not hi:
        return ""
    return f"{1e6 / ((int(lo) + int(hi)) / 2):.2f}"


def analyse() -> tuple:
    data, summary, excluded = {}, [], []
    for scn in SCENARIOS:
        path = MEAS / f"{scn}.csv"
        if not path.exists():
            print(f"UYARI: {path.name} yok, atlandı")
            continue
        rows = load_event_csv(path)
        data[scn] = rows
        cnt = load_counters(scn)

        # Timing statistics use only complete, successful events
        good = [r for r in rows if r.ok and all(v is not None for v in r.t)]
        for r in rows:
            if r not in good:
                missing = [f"t{i}" for i, v in enumerate(r.t) if v is None]
                excluded.append((scn, r.event_id, r.status,
                                 "eksik: " + ",".join(missing) if missing else "durum ok değil"))

        R = [r.r_us for r in good]
        stages = [[r.stage_us(i) for r in good] for i in range(4)]
        # Press spacing from the board's own t0 stamps (procedure: >= 0.5 s)
        t0s = [r.t[0] for r in rows if r.t[0] is not None]
        gaps = [((b - a) & 0xFFFFFFFF) / 1e6 for a, b in zip(t0s, t0s[1:])]
        status = {s: sum(r.status == s for r in rows)
                  for s in ("btn_drop", "tx_drop", "tx_error", "timeout")}
        summary.append({
            "scenario": scn,
            "accepted": len(rows),
            "ok": len(good),
            "r_min_ms": round(ms(min(R)), 3),
            "r_mean_ms": round(ms(mean(R)), 3),
            "r_median_ms": round(ms(median(R)), 3),
            "r_p95_ms": round(ms(p95(R)), 3),
            "r_max_ms": round(ms(max(R)), 3),
            "over_deadline": sum(v > DEADLINE_US for v in R),
            "drop": status["btn_drop"] + status["tx_drop"],
            "btn_drop": status["btn_drop"],
            "tx_drop": status["tx_drop"],
            "tx_error": status["tx_error"],
            "timeout": status["timeout"],
            "log_overflow": int(cnt.get("log_overflow", "0") or 0),
            "t1_t0_mean_ms": round(ms(mean(stages[0])), 3),
            "t2_t1_mean_ms": round(ms(mean(stages[1])), 3),
            "t3_t2_mean_ms": round(ms(mean(stages[2])), 3),
            "t4_t3_mean_ms": round(ms(mean(stages[3])), 3),
            "t1_t0_max_ms": round(ms(max(stages[0])), 3),
            "t3_t2_max_ms": round(ms(max(stages[2])), 3),
            "tx_drop_tel": int(cnt.get("tx_drop_tel", "0") or 0),
            "bounce_rejected": int(cnt.get("bounce_rejected", "0") or 0),
            "tel_period_min_us": cnt.get("tel_period_min_us", ""),
            "tel_period_max_us": cnt.get("tel_period_max_us", ""),
            "work_min_us": cnt.get("work_min_us", ""),
            "work_max_us": cnt.get("work_max_us", ""),
            "press_gap_min_s": round(min(gaps), 3) if gaps else "",
            "press_gap_median_s": round(median(gaps), 3) if gaps else "",
            "press_gap_under_0_5s": sum(g < MIN_PRESS_GAP_S for g in gaps),
            "tel_rate_hz": tel_rate(cnt),
            "txq_hwm": cnt.get("txq_hwm", ""),
            "txq_hwm_tel": cnt.get("txq_hwm_tel", ""),
            "txq_hwm_btn": cnt.get("txq_hwm_btn", ""),
            "btnq_hwm": cnt.get("btnq_hwm", ""),
        })
    return data, summary, excluded


def write_summary(summary: list) -> None:
    path = MEAS / "summary.csv"
    with open(path, "w", newline="", encoding="ascii") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(summary)
    print(f"yazıldı: {path.relative_to(ROOT)}")


def write_plots(data: dict) -> None:
    PLOTS.mkdir(exist_ok=True)

    # Plot 1: event -> R with the deadline, one panel per scenario
    fig = Figure(figsize=(16, 9), layout="constrained")
    axes = fig.subplots(2, 3)
    for ax, scn in zip(axes.flat, SCENARIOS):
        plots.plot_r(ax, data.get(scn, []), f"· {scn} ({SCN_DESC[scn]})")
    fig.suptitle("Olay numarası → yanıt süresi R = t₄ − t₀ (kesikli çizgi: 20 ms deadline)",
                 fontsize=13, x=0.01, ha="left")
    plots.apply_style(fig)
    out = PLOTS / "r_per_event.png"
    fig.savefig(out, dpi=110)
    print(f"yazıldı: {out.relative_to(ROOT)}")

    # Plot 2: scenario -> mean stage durations (stacked) + observed max R
    fig = Figure(figsize=(12, 6), layout="constrained")
    ax = fig.add_subplot(111)
    plots.plot_compare(ax, data)
    plots.apply_style(fig)
    out = PLOTS / "stage_means.png"
    fig.savefig(out, dpi=110)
    print(f"yazıldı: {out.relative_to(ROOT)}")


PERIOD_US = {"S1": 100_000, "S2": 20_000, "S3": 10_000, "S4": 10_000, "S5": 10_000}
LINE_US = 5_559          # measured t4 - t3, one 64-byte frame
WAIT_THRESHOLD_US = 1_000
PLATEAU_FROM_EVENT = 15  # S5: events from here on are in the saturated regime (see plot 1)


def extra_observations() -> list:
    """Numbers quoted in the report text beyond the main tables."""
    out = ["| Senaryo | Hat doluluğu (%) | t₃ − t₂ > 1 ms olan olay | t₃ faz bandı (t₃ mod periyot, µs) |",
           "|---|---|---|---|"]
    for scn in ("S1", "S2", "S3", "S4", "S5"):
        path = MEAS / f"{scn}.csv"
        if not path.exists():
            continue
        rows = load_event_csv(path)
        good = [r for r in rows if r.ok and all(v is not None for v in r.t)]
        waits = sum(r.stage_us(2) > WAIT_THRESHOLD_US for r in good)
        phase = [r.t[3] % PERIOD_US[scn] for r in good]
        util = 100.0 * LINE_US / PERIOD_US[scn]
        out.append(f"| {scn} | {util:.1f} | {waits} / {len(good)} | {min(phase)}–{max(phase)} |")
    s5 = MEAS / "S5.csv"
    if s5.exists():
        good = [r for r in load_event_csv(s5) if r.ok and r.r_us is not None]
        plateau = [r.r_us for r in good if r.event_id >= PLATEAU_FROM_EVENT]
        if plateau:
            out += ["", f"S5 plato: olay ≥ {PLATEAU_FROM_EVENT} için R ort = "
                        f"{fmt(ms(mean(plateau)))} ms (n = {len(plateau)}). "
                        f"Kuyruk uzunluğu × periyot = 16 × 10 ms = 160 ms."]
    return out


def fmt(v: float) -> str:
    return f"{v:.3f}".replace(".", ",")


def write_tables(summary: list, excluded: list) -> None:
    lines = ["# Betik çıktısı: rapor tabloları", "",
             "Bu dosya `analysis/analyze.py` tarafından üretilir; elle düzenlenmez.", "",
             "## Özet tablo (ms)", "",
             "| Senaryo | Kabul edilen olay | Başarılı (ok) | R min | R ort | R medyan | R p95 | "
             "R maks (gözlenen) | > 20 ms | drop | tx_error | timeout | Kayıt kaybı |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in summary:
        lines.append(
            f"| {s['scenario']} | {s['accepted']} | {s['ok']} | {fmt(s['r_min_ms'])} | "
            f"{fmt(s['r_mean_ms'])} | {fmt(s['r_median_ms'])} | {fmt(s['r_p95_ms'])} | "
            f"{fmt(s['r_max_ms'])} | {s['over_deadline']} | {s['drop']} | {s['tx_error']} | "
            f"{s['timeout']} | {s['log_overflow']} |")
    lines += ["", "## Aşama süreleri (ms, başarılı olayların ortalaması)", "",
              "| Senaryo | t₁ − t₀ | t₂ − t₁ | t₃ − t₂ | t₄ − t₃ | R |",
              "|---|---|---|---|---|---|"]
    for s in summary:
        lines.append(
            f"| {s['scenario']} | {fmt(s['t1_t0_mean_ms'])} | {fmt(s['t2_t1_mean_ms'])} | "
            f"{fmt(s['t3_t2_mean_ms'])} | {fmt(s['t4_t3_mean_ms'])} | {fmt(s['r_mean_ms'])} |")
    lines += ["", "## Kart sayaçları", "",
              "| Senaryo | Gerçek telemetri hızı (Hz) | periyot min/maks (µs) | CPU işi min/maks (µs) | "
              "TX kuyruğu HWM (/16) | Buton kuyruğu HWM (/8) | tx_drop_tel | bounce_rejected |",
              "|---|---|---|---|---|---|---|---|"]
    for s in summary:
        per = f"{s['tel_period_min_us']} / {s['tel_period_max_us']}" if s["tel_period_min_us"] else "—"
        work = f"{s['work_min_us']} / {s['work_max_us']}" if s["work_min_us"] else "—"
        rate = s["tel_rate_hz"].replace(".", ",") if s["tel_rate_hz"] else "kapalı"
        txq = s["txq_hwm"] or "ölçülmedi"
        btq = s["btnq_hwm"] or "ölçülmedi"
        lines.append(f"| {s['scenario']} | {rate} | {per} | {work} | {txq} | {btq} | "
                     f"{s['tx_drop_tel']} | {s['bounce_rejected']} |")
    lines += ["", "## Prosedür kontrolü (basış aralıkları, kartın t₀ damgalarından)", "",
              "| Senaryo | Kabul edilen olay | Basış aralığı min (s) | medyan (s) | 0,5 s'den kısa |",
              "|---|---|---|---|---|"]
    for s in summary:
        lines.append(f"| {s['scenario']} | {s['accepted']} | {str(s['press_gap_min_s']).replace('.', ',')} | "
                     f"{str(s['press_gap_median_s']).replace('.', ',')} | {s['press_gap_under_0_5s']} |")
    lines += ["", "## Ek gözlemler", ""] + extra_observations() + ["", "## Dışlanan kayıtlar", ""]
    if excluded:
        lines += ["Zaman istatistiklerinden dışlandı; özet tablodaki olay sayılarında ve kayıp sütunlarında yer alır.", "",
                  "| Senaryo | Olay | Durum | Neden |", "|---|---|---|---|"]
        lines += [f"| {s} | {e} | {st} | {why} |" for s, e, st, why in excluded]
    else:
        lines.append("Yok.")
    out = HERE / "tables.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"yazıldı: {out.relative_to(ROOT)}")


def main() -> None:
    data, summary, excluded = analyse()
    if not summary:
        sys.exit("measurements/ altında Sx.csv bulunamadı")
    write_summary(summary)
    write_plots(data)
    write_tables(summary, excluded)
    print("\nDışlanan kayıtlar:")
    for scn, eid, st, why in excluded or [("-", "-", "-", "yok")]:
        print(f"  {scn} olay {eid}: {st} ({why})")


if __name__ == "__main__":
    main()
