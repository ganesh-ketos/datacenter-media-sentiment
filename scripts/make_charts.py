#!/usr/bin/env python3
"""Generate publication charts (PNG) from the processed monthly datasets.

Reads data/processed/monthly_volume.csv and, when present,
data/processed/monthly_sentiment.csv. Writes PNGs to charts/.
"""

import csv
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

ROOT = Path(__file__).resolve().parent.parent
CHARTS = ROOT / "charts"

# palette (light mode)
BLUE = "#2a78d6"
BLUE_LIGHT = "#9ec5f4"
RED = "#e34948"
AQUA = "#1baf7a"
YELLOW = "#eda100"
VIOLET = "#4a3aa7"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SURFACE = "#fcfcfb"

CHATGPT = date(2022, 11, 30)

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Arial", "DejaVu Sans"],
    "text.color": INK,
    "axes.edgecolor": AXIS,
    "axes.labelcolor": INK_2,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "savefig.dpi": 200,
})


def month_to_date(m: str) -> date:
    y, mo = m.split("-")
    return date(int(y), int(mo), 15)


def style_axes(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def annotate_chatgpt(ax, y_frac=0.94):
    ax.axvline(CHATGPT, color=INK_2, linewidth=1.2, linestyle=(0, (4, 3)))
    ax.text(CHATGPT, ax.get_ylim()[1] * y_frac, "  ChatGPT launches\n  Nov 30, 2022",
            color=INK_2, fontsize=9, va="top", ha="left")


def load_volume():
    with open(ROOT / "data/processed/monthly_volume.csv") as f:
        return list(csv.DictReader(f))


def chart_volume_count(rows):
    months = [month_to_date(r["month"]) for r in rows]
    counts = [int(r["article_count"]) for r in rows]
    # months with missing days (GDELT outages) rendered lighter
    partial = [int(r["days_with_data"]) < 27 for r in rows]
    colors = [BLUE_LIGHT if p else BLUE for p in partial]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(months, counts, width=24, color=colors, edgecolor=SURFACE, linewidth=0.8)
    for m, c, p in zip(months, counts, partial):
        if p:
            ax.annotate("partial\nmonth", xy=(m, c), xytext=(0, 4),
                        textcoords="offset points", ha="center",
                        fontsize=7, color=MUTED)
    style_axes(ax)
    ax.set_ylim(0, max(counts) * 1.12)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v / 1000:.0f}k"))
    annotate_chatgpt(ax)
    peak = max(zip(counts, months))
    ax.annotate(f"{peak[0]:,}", xy=(peak[1], peak[0]), xytext=(0, 5),
                textcoords="offset points", ha="center", fontsize=9, color=INK_2)
    ax.set_title("English-language news articles mentioning data centers, per month",
                 fontsize=13, color=INK, loc="left", pad=14)
    fig.text(0.01, 0.015,
             "Source: GDELT DOC 2.0 API. Query: \"data center(s)\" / \"datacenter(s)\", English sources worldwide. "
             "GDELT outage Jun 15 – Jul 1, 2025 (partial month).",
             fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(CHARTS / "01_monthly_article_count.png")
    plt.close(fig)


def chart_volume_share(rows):
    months = [month_to_date(r["month"]) for r in rows]
    share = [float(r["avg_daily_volume_pct"]) for r in rows]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.fill_between(months, share, color=BLUE_LIGHT, alpha=0.45, linewidth=0)
    ax.plot(months, share, color=BLUE, linewidth=2)
    style_axes(ax)
    ax.set_ylim(0, max(share) * 1.15)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.2f}%"))
    annotate_chatgpt(ax)
    first, last = share[0], share[-1]
    ax.annotate(f"{last:.2f}% of all\nmonitored articles", xy=(months[-1], last),
                xytext=(-8, 12), textcoords="offset points", ha="right",
                fontsize=9, color=INK_2)
    ax.set_title(
        f"Share of global English news coverage mentioning data centers "
        f"({last / first:.1f}x since Jan 2022)",
        fontsize=13, color=INK, loc="left", pad=14)
    fig.text(0.01, 0.015,
             "Source: GDELT DOC 2.0 API. Monthly mean of daily share of all GDELT-monitored English articles "
             "(normalizes for growth in GDELT's coverage).",
             fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(CHARTS / "02_monthly_volume_share.png")
    plt.close(fig)


def chart_sentiment(vol_rows):
    path = ROOT / "data/processed/monthly_sentiment.csv"
    if not path.exists():
        print("monthly_sentiment.csv not found - skipping sentiment charts")
        return
    with open(path) as f:
        rows = list(csv.DictReader(f))
    months = [month_to_date(r["month"]) for r in rows]
    pos = [100 * float(r["positive_share"]) for r in rows]
    neg = [100 * float(r["negative_share"]) for r in rows]
    neu = [100 * float(r["neutral_share"]) for r in rows]
    net = [100 * float(r["net_sentiment"]) for r in rows]

    # sentiment shares (stacked bars) - positive blue, neutral gray, negative red
    fig, ax = plt.subplots(figsize=(10, 5.5))
    width = 24
    ax.bar(months, pos, width=width, color=BLUE, edgecolor=SURFACE,
           linewidth=0.8, label="Positive")
    ax.bar(months, neu, width=width, bottom=pos, color="#d9d8d2",
           edgecolor=SURFACE, linewidth=0.8, label="Neutral")
    ax.bar(months, neg, width=width, bottom=[p + n for p, n in zip(pos, neu)],
           color=RED, edgecolor=SURFACE, linewidth=0.8, label="Negative")
    style_axes(ax)
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    annotate_chatgpt(ax)
    ax.legend(frameon=False, loc="lower left", ncol=3, fontsize=9,
              bbox_to_anchor=(0, 1.0))
    ax.set_title("Sentiment of data center news headlines toward data centers",
                 fontsize=13, color=INK, loc="left", pad=30)
    fig.text(0.01, 0.015,
             "LLM classification (Claude Sonnet) of 150 randomly sampled datacenter-headlined articles/month "
             "from GDELT's Global Knowledge Graph (103k-article census). Shares of relevant headlines. "
             "Rubric committed in repo.",
             fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(CHARTS / "03_sentiment_shares.png")
    plt.close(fig)

    # net sentiment line
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.axhline(0, color=AXIS, linewidth=1)
    ax.fill_between(months, net, 0, where=[v >= 0 for v in net],
                    color=BLUE_LIGHT, alpha=0.5, interpolate=True, linewidth=0)
    ax.fill_between(months, net, 0, where=[v < 0 for v in net],
                    color="#f5b5b4", alpha=0.6, interpolate=True, linewidth=0)
    ax.plot(months, net, color=INK_2, linewidth=2)
    style_axes(ax)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}pp"))
    annotate_chatgpt(ax)
    ax.set_title("Net sentiment of data center headlines (% positive - % negative)",
                 fontsize=13, color=INK, loc="left", pad=14)
    fig.text(0.01, 0.015,
             "LLM classification of monthly headline samples from GDELT (n<=150/month). "
             "Above zero: positive coverage outweighs negative.",
             fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(CHARTS / "04_net_sentiment.png")
    plt.close(fig)

    # GDELT tone overlay (cross-validation) - indexed panels, one axis each
    with open(ROOT / "data/processed/monthly_headline_census.csv") as f:
        tone = {r["month"]: float(r["avg_tone"]) for r in csv.DictReader(f)}
    tone_series = [tone[r["month"]] for r in rows]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    ax1.axhline(0, color=AXIS, linewidth=1)
    ax1.plot(months, net, color=BLUE, linewidth=2)
    ax1.set_ylabel("Net sentiment (pp)", fontsize=9)
    ax2.axhline(0, color=AXIS, linewidth=1)
    ax2.plot(months, tone_series, color=VIOLET, linewidth=2)
    ax2.set_ylabel("GDELT avg tone", fontsize=9)
    for ax in (ax1, ax2):
        style_axes(ax)
    ax1.set_title("Two independent measures, same downward drift",
                  fontsize=13, color=INK, loc="left", pad=14)
    fig.text(0.01, 0.015,
             "Top: LLM-classified headline sentiment (150/month sample). "
             "Bottom: GDELT lexicon tone across all 103,341 datacenter-headlined articles (population-wide, "
             "independent of the LLM).",
             fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(CHARTS / "05_tone_crossvalidation.png")
    plt.close(fig)

    # theme mix over time (share of relevant headlines), quarterly averaged
    themes = [("theme_energy_grid", "Energy & grid", BLUE),
              ("theme_environment_water", "Environment & water", AQUA),
              ("theme_community_opposition", "Community opposition", RED),
              ("theme_investment_buildout", "Investment & buildout", YELLOW)]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for key, label, color in themes:
        vals = [100 * float(r[key]) for r in rows]
        # 3-month centered rolling mean to reduce sample noise
        smooth = [sum(vals[max(0, i - 1):i + 2]) / len(vals[max(0, i - 1):i + 2])
                  for i in range(len(vals))]
        ax.plot(months, smooth, color=color, linewidth=2, label=label)
        ax.annotate(label, xy=(months[-1], smooth[-1]), xytext=(6, 0),
                    textcoords="offset points", fontsize=8.5, color=color,
                    va="center")
    style_axes(ax)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    annotate_chatgpt(ax)
    ax.set_title("What data center coverage is about (share of headlines, 3-mo avg)",
                 fontsize=13, color=INK, loc="left", pad=14)
    fig.subplots_adjust(right=0.82)
    fig.text(0.01, 0.015,
             "Theme of each sampled headline, LLM-classified. Four most dynamic themes shown; "
             "investment/buildout, tech/operations, policy and other omitted lines sum to 100%.",
             fontsize=7.5, color=MUTED)
    fig.savefig(CHARTS / "06_theme_mix.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    CHARTS.mkdir(exist_ok=True)
    vol = load_volume()
    chart_volume_count(vol)
    chart_volume_share(vol)
    chart_sentiment(vol)
    print("Charts written to", CHARTS)


if __name__ == "__main__":
    main()
