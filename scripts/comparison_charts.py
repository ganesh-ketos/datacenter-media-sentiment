#!/usr/bin/env python3
"""Cross-technology backlash charts from data/processed/comparison_monthly.csv.

Chart 08: tone change aligned to each technology's coverage-boom start
          (takeoff = first month with 3-mo mean count >= max(500, 2x median of
          all prior months), sustained 3 months).
Chart 09: months from goodwill peak to sustained net-negative tone, where the
          goodwill peak anchors the 24 months before each technology's steepest
          18-month tone decline, and "turned" means 2 consecutive 3-mo-smoothed
          months below zero.
"""

import csv
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
BLUE, RED, AQUA, YELLOW, VIOLET, MAGENTA = \
    "#2a78d6", "#e34948", "#1baf7a", "#eda100", "#4a3aa7", "#e87ba4"
INK, INK2, MUTED, GRID, AXIS, SURFACE = \
    "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
COLORS = {"datacenter": BLUE, "fracking": RED, "wind": AQUA,
          "solar": YELLOW, "5g": VIOLET, "crypto_mining": MAGENTA}
LABELS = {"datacenter": "Data centers", "fracking": "Fracking", "wind": "Wind farms",
          "solar": "Solar farms", "5g": "5G", "crypto_mining": "Crypto mining"}

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Arial", "DejaVu Sans"],
    "text.color": INK, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE, "savefig.dpi": 200,
})


def load():
    vol, tone = defaultdict(dict), defaultdict(dict)
    with open(ROOT / "data/processed/comparison_monthly.csv") as f:
        for r in csv.DictReader(f):
            vol[r["topic"]][r["month"]] = int(r["article_count"])
            tone[r["topic"]][r["month"]] = float(r["avg_tone"])
    return vol, tone


def smoothed(series, k):
    months = sorted(series)
    vals = [series[m] for m in months]
    return months, [sum(vals[max(0, i-k+1):i+1]) / len(vals[max(0, i-k+1):i+1])
                    for i in range(len(vals))]


def takeoff(mono):
    months = sorted(mono)
    counts = [mono[m] for m in months]
    for i in range(12, len(months) - 3):
        if all(c >= max(500, 2 * statistics.median(counts[:i]))
               for c in counts[i:i+3]):
            return months[i]
    return None


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def chart_aligned(vol, tone):
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.axhline(0, color=AXIS, linewidth=1)
    for t in ("5g", "crypto_mining", "datacenter"):
        t0 = takeoff(vol[t])
        months, sm = smoothed(tone[t], 6)
        i0 = months.index(t0)
        base = statistics.mean(sm[max(0, i0-12):i0])
        xs = list(range(0, min(36, len(sm) - i0)))
        ys = [sm[i0 + x] - base for x in xs]
        lw = 3 if t == "datacenter" else 2
        ax.plot(xs, ys, color=COLORS[t], linewidth=lw)
        ax.annotate(f"{LABELS[t]}  (boom: {t0})", xy=(xs[-1], ys[-1]),
                    xytext=(6, 0), textcoords="offset points",
                    color=COLORS[t], fontsize=9.5, va="center")
    solar_months, solar_sm = smoothed(tone["solar"], 6)
    var = statistics.pstdev(solar_sm)
    ax.axhspan(-var, var, color=YELLOW, alpha=0.10)
    ax.text(35.5, var + 0.03, "solar's entire 11-year range", color="#b07f10",
            fontsize=8.5, ha="right")
    style(ax)
    ax.set_xlabel("Months since coverage boom began", fontsize=10)
    ax.set_ylabel("Change in press tone since boom began", fontsize=10)
    ax.set_title("After the boom, how fast does the press turn?",
                 fontsize=14, color=INK, loc="left", pad=14)
    fig.text(0.01, 0.015,
             "GDELT average tone of headline coverage, 6-month rolling mean, "
             "relative to each technology's pre-boom year. Boom = first sustained "
             "doubling of monthly coverage. Data through June 2026.",
             fontsize=7.5, color=MUTED)
    fig.subplots_adjust(right=0.78)
    fig.savefig(ROOT / "charts/08_backlash_aligned.png", bbox_inches="tight")
    plt.close(fig)


def chart_time_to_flip(vol, tone):
    drops = {}
    for t in tone:
        months, sm = smoothed(tone[t], 6)
        best = (0, 0)
        for i in range(len(sm) - 18):
            if sm[i] - sm[i+18] > best[0]:
                best = (sm[i] - sm[i+18], i)
        drops[t] = best[1]
    rows = []
    for t in tone:
        months, sm3 = smoothed(tone[t], 3)
        di = drops[t]
        lo = max(0, di - 24)
        pk = lo + max(range(lo, di + 1), key=lambda i: sm3[i]) - lo
        pk = max(range(lo, di + 1), key=lambda i: sm3[i])
        if sm3[pk] < 0:
            rows.append((t, None, "hostile throughout"))
            continue
        cross = None
        for i in range(pk, len(sm3) - 1):
            if sm3[i] < 0 and sm3[i+1] < 0:
                cross = i
                break
        if cross is None:
            rows.append((t, None, "never turned"))
        else:
            rec = next((i for i in range(cross, len(sm3) - 1)
                        if sm3[i] > 0 and sm3[i+1] > 0), None)
            note = f"recovered after {rec - cross} mo" if rec else "still negative"
            rows.append((t, cross - pk, note))

    fig, ax = plt.subplots(figsize=(10, 5))
    order = sorted(rows, key=lambda r: (r[1] is None, r[1] if r[1] else 0))
    ys = range(len(order))
    for y, (t, val, note) in zip(ys, order):
        if val is None:
            ax.barh(y, 40, color=GRID, height=0.55)
            ax.text(1, y, f"{LABELS[t]}: {note}", va="center", fontsize=10,
                    color=INK2)
        else:
            hl = t == "datacenter"
            ax.barh(y, val, color=COLORS[t], height=0.55)
            ax.text(val + 0.6, y, f"{LABELS[t]}: {val} months ({note})",
                    va="center", fontsize=11 if hl else 10,
                    color=INK if hl else INK2,
                    fontweight="bold" if hl else "normal")
    ax.set_yticks([])
    style(ax)
    ax.set_xlabel("Months from goodwill peak to sustained net-negative press",
                  fontsize=10)
    ax.set_title("How long each technology held onto its good press",
                 fontsize=14, color=INK, loc="left", pad=14)
    fig.text(0.01, 0.015,
             "GDELT tone of headline coverage, 3-month smoothed. Goodwill peak = "
             "highest tone in the 2 years before each technology's steepest decline. "
             "Turned = 2 consecutive months below zero. Data through June 2026.",
             fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(ROOT / "charts/09_time_to_flip.png", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    vol, tone = load()
    chart_aligned(vol, tone)
    chart_time_to_flip(vol, tone)
    print("wrote charts/08_backlash_aligned.png and charts/09_time_to_flip.png")
