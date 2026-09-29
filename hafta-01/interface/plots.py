"""Matplotlib chart builders shared by the GUI (and reusable by analysis scripts).

Each function draws on a given Axes, so the same chart can be embedded in
Tk or saved to a PNG file.
"""
from __future__ import annotations

import random
from statistics import mean

from protocol import STAGE_NAMES

DEADLINE_MS = 20.0

# One fixed colour per stage, used by every chart for consistency
STAGE_COLORS = ("#4C72B0", "#55A868", "#DD8452", "#8172B3")
STAGE_TEXT = (
    "t₁−t₀  ISR → ButtonTask",
    "t₂−t₁  yanıt hazırlama",
    "t₃−t₂  TX kuyruğu + UART başlatma",
    "t₄−t₃  hat süresi + TC",
)
COLOR_OK = "#2A9D8F"
COLOR_LATE = "#E76F51"
COLOR_DROP = "#8D99AE"
COLOR_DEADLINE = "#D62828"


def apply_style(fig) -> None:
    fig.patch.set_facecolor("white")
    for ax in fig.axes:
        style_axes(ax)


def style_axes(ax) -> None:
    ax.set_facecolor("#FAFAFA")
    ax.grid(True, color="#E0E0E0", linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def _empty(ax, text: str) -> None:
    ax.text(0.5, 0.5, text, ha="center", va="center", transform=ax.transAxes,
            fontsize=11, color="#888888")


def plot_live(ax, rate_hist, btn_marks, window_s: float) -> None:
    """TEL messages per second over time, BTN events as vertical markers."""
    ax.clear()
    style_axes(ax)
    ax.set_title("Canlı akış: TEL mesaj/s ve buton olayları", loc="left", fontsize=11)
    ax.set_xlabel("süre (s, PC saati)")
    ax.set_ylabel("TEL mesaj / s")
    if not rate_hist:
        _empty(ax, "Veri bekleniyor…")
        return
    t_end = rate_hist[-1][0]
    xs = [t - t_end for t, _ in rate_hist]
    ys = [r for _, r in rate_hist]
    ax.plot(xs, ys, color="#4C72B0", linewidth=2)
    ax.fill_between(xs, ys, color="#4C72B0", alpha=0.12)
    for t, eid in btn_marks:
        x = t - t_end
        if x >= -window_s:
            ax.axvline(x, color=COLOR_LATE, linewidth=1.2, alpha=0.8)
            ax.text(x, ax.get_ylim()[1] * 0.95 if max(ys) > 0 else 1, f" {eid}",
                    color=COLOR_LATE, fontsize=8, va="top")
    ax.set_xlim(-window_s, 0)
    ax.set_ylim(0, max(10, max(ys) * 1.25))


def plot_r(ax, rows, title_suffix: str = "") -> None:
    """Event number -> R = t4 - t0, with the 20 ms deadline line."""
    ax.clear()
    style_axes(ax)
    ax.set_title(f"Olay → yanıt süresi R = t₄ − t₀ {title_suffix}", loc="left", fontsize=11)
    ax.set_xlabel("olay no")
    ax.set_ylabel("R (ms)")
    if not rows:
        _empty(ax, "DUMP bekleniyor…")
        return

    ok_x, ok_y, late_x, late_y, bad_x = [], [], [], [], []
    for r in rows:
        if r.ok and r.r_us is not None:
            ms = r.r_us / 1000.0
            (late_x if ms > DEADLINE_MS else ok_x).append(r.event_id)
            (late_y if ms > DEADLINE_MS else ok_y).append(ms)
        else:
            bad_x.append(r.event_id)

    ax.vlines(ok_x, 0, ok_y, color=COLOR_OK, alpha=0.35, linewidth=1)
    ax.vlines(late_x, 0, late_y, color=COLOR_LATE, alpha=0.35, linewidth=1)
    ax.scatter(ok_x, ok_y, color=COLOR_OK, s=36, zorder=3, label="ok, ≤ 20 ms")
    ax.scatter(late_x, late_y, color=COLOR_LATE, s=36, zorder=3, label="ok, > 20 ms")
    if bad_x:
        ax.scatter(bad_x, [0] * len(bad_x), marker="x", color=COLOR_DROP, s=50,
                   zorder=3, label="kayıp / hata (R yok)")
    ax.axhline(DEADLINE_MS, color=COLOR_DEADLINE, linestyle="--", linewidth=1.5,
               label="deadline 20 ms")

    vals = ok_y + late_y
    if vals:
        info = (f"n={len(rows)}  ok={len(vals)}  ort={mean(vals):.2f} ms  "
                f"maks={max(vals):.2f} ms  >20 ms: {len(late_y)}  kayıp: {len(bad_x)}")
        ax.text(0.99, 0.02, info, transform=ax.transAxes, fontsize=9, color="#333333",
                va="bottom", ha="right",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#DDDDDD"))
        ax.set_ylim(0, max(DEADLINE_MS * 1.3, max(vals) * 1.15))
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)


def plot_stages(ax, rows) -> None:
    """Horizontal stacked bar per event: a t0 -> t4 timeline, time flows left to right."""
    ax.clear()
    style_axes(ax)
    ax.set_title("Olay başına aşama süreleri (t₀ → t₄ zaman çizelgesi)", loc="left", fontsize=11)
    ax.set_xlabel("t₀'dan itibaren süre (ms)")
    ax.set_ylabel("olay no")
    good = [r for r in rows if r.ok and all(v is not None for v in r.t)]
    if not good:
        _empty(ax, "DUMP bekleniyor…")
        return
    y = [r.event_id for r in good]
    left = [0.0] * len(good)
    for i in range(4):
        w = [r.stage_us(i) / 1000.0 for r in good]
        ax.barh(y, w, left=left, color=STAGE_COLORS[i], height=0.75,
                label=STAGE_TEXT[i], edgecolor="white", linewidth=0.4)
        left = [a + b for a, b in zip(left, w)]
    ax.axvline(DEADLINE_MS, color=COLOR_DEADLINE, linestyle="--", linewidth=1.2,
               label="deadline 20 ms")
    if len(y) <= 40:
        ax.set_yticks(y)
    ax.invert_yaxis()   # event 1 at the top, reads like a log
    ax.grid(True, axis="x", color="#E0E0E0")
    ax.grid(False, axis="y")
    ax.set_xlim(0, max(DEADLINE_MS, max(left)) * 1.08)
    _legend_below(ax)


def plot_distribution(ax, rows) -> None:
    """Every stage and R as jittered points on a log scale (us)."""
    ax.clear()
    style_axes(ax)
    ax.set_title("Aşama dağılımları (log ölçek, µs)", loc="left", fontsize=11)
    ax.set_ylabel("süre (µs, log)")
    good = [r for r in rows if r.ok and all(v is not None for v in r.t)]
    if not good:
        _empty(ax, "DUMP bekleniyor…")
        return
    rng = random.Random(1)  # fixed seed: same picture for the same data
    names = list(STAGE_NAMES) + ["R"]
    colors = list(STAGE_COLORS) + [COLOR_OK]
    for k, name in enumerate(names):
        vals = [(r.stage_us(k) if k < 4 else r.r_us) for r in good]
        vals = [max(v, 1) for v in vals]
        xs = [k + rng.uniform(-0.18, 0.18) for _ in vals]
        ax.scatter(xs, vals, s=22, color=colors[k], alpha=0.75, zorder=3)
        ax.hlines(mean(vals), k - 0.3, k + 0.3, color="#222222", linewidth=2, zorder=4)
        ax.text(k + 0.32, mean(vals), f"{mean(vals):.0f}", fontsize=8, va="center")
    ax.axhline(DEADLINE_MS * 1000, color=COLOR_DEADLINE, linestyle="--", linewidth=1.2)
    ax.set_yscale("log")
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(["t₁−t₀", "t₂−t₁", "t₃−t₂", "t₄−t₃", "R"])
    ax.set_xlim(-0.6, len(names) - 0.2)


def plot_compare(ax, data: dict) -> None:
    """Scenario -> mean stage durations (stacked) plus observed max R."""
    ax.clear()
    style_axes(ax)
    ax.set_title("Senaryo karşılaştırması: ortalama aşamalar ve gözlenen maks R",
                 loc="left", fontsize=11)
    ax.set_xlabel("süre (ms)")
    if not data:
        _empty(ax, "measurements/ altında Sx.csv yok")
        return
    names = sorted(data)
    ys = list(range(len(names)))
    left = [0.0] * len(names)
    r_max = 0.0
    for i in range(4):
        w = []
        for n in names:
            good = [r for r in data[n] if r.ok and all(v is not None for v in r.t)]
            w.append(mean(r.stage_us(i) for r in good) / 1000.0 if good else 0.0)
        ax.barh(ys, w, left=left, color=STAGE_COLORS[i], label=STAGE_TEXT[i],
                height=0.6, edgecolor="white")
        left = [a + b for a, b in zip(left, w)]
    for k, n in enumerate(names):
        rs = [r.r_us / 1000.0 for r in data[n] if r.ok and r.r_us is not None]
        if rs:
            r_max = max(r_max, max(rs))
            ax.scatter([max(rs)], [k], marker="D", color="#222222", s=30, zorder=4)
            ax.text(max(rs), k, f"  maks {max(rs):.1f}", fontsize=8, va="center", ha="left")
    ax.axvline(DEADLINE_MS, color=COLOR_DEADLINE, linestyle="--", linewidth=1.2,
               label="deadline 20 ms")
    ax.set_yticks(ys)
    ax.set_yticklabels(names)
    ax.invert_yaxis()   # S0 at the top
    ax.grid(False, axis="y")
    ax.set_xlim(0, max(DEADLINE_MS, r_max, max(left)) * 1.2)   # room for the max labels
    _legend_below(ax)


def _legend_below(ax) -> None:
    """Legend under the plot area so it never hides long bars."""
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=3, fontsize=8,
              frameon=False)
