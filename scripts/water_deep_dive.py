#!/usr/bin/env python3
"""Water-coverage deep dive: when did water become a mainstream datacenter issue,
how fast is it growing vs energy, and where does it rank among backlash themes.

Two independent signals:
  1. Theme shares from the LLM-classified sample (census_classified.csv,
     environment_water vs energy_grid, share of relevant headlines).
  2. Keyword frequency over the full 103k headline-frame census
     (bigquery_census.csv has no titles, so keywords are matched against
     URL slug tokens; the proxy is validated against the 8,100 fetched titles).

Inputs:
  data/processed/census_classified.csv
  data/raw/bigquery_census.csv

Outputs:
  data/processed/water_deep_dive_monthly.csv
  data/processed/water_deep_dive_quarterly.csv
  charts/10_water_vs_energy.png
  charts/11_backlash_theme_ranking.png
  Summary stats printed to stdout.
"""

import csv
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CHARTS = ROOT / "charts"

THEMES = ["energy_grid", "environment_water", "community_opposition",
          "investment_buildout", "jobs_economy", "policy_regulation",
          "tech_operations", "other"]
THEME_LABELS = {
    "energy_grid": "Energy & grid",
    "environment_water": "Environment & water",
    "community_opposition": "Community opposition",
    "investment_buildout": "Investment & buildout",
    "jobs_economy": "Jobs & economy",
    "policy_regulation": "Policy & regulation",
    "tech_operations": "Tech & operations",
    "other": "Other",
}

# exact-token match so waterloo/stillwater/watertown don't false-positive
WATER_KW = {"water", "drought", "aquifer", "groundwater", "wastewater"}
ENERGY_KW = {"power", "energy", "electricity", "grid", "megawatt", "megawatts",
             "nuclear"}

EARLY = ("2022-01", "2023-12")   # pre/early-boom baseline
LATE = ("2025-01", "2026-06")    # most recent 18 months

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


def quarter_of(m: str) -> str:
    y, mo = m.split("-")
    return f"{y}-Q{(int(mo) - 1) // 3 + 1}"


def quarter_to_date(q: str) -> date:
    y, qn = q.split("-Q")
    return date(int(y), (int(qn) - 1) * 3 + 2, 15)


def tokens(text: str) -> set:
    return set(re.split(r"[^a-z]+", text.lower())) - {""}


def url_tokens(url: str) -> set:
    return tokens(urlparse(url).path)


def in_period(m: str, period) -> bool:
    return period[0] <= m <= period[1]


def style_axes(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def load_classified():
    with open(DATA / "processed" / "census_classified.csv") as f:
        return list(csv.DictReader(f))


def load_census():
    """Full headline-frame census, deduped by URL (same rule as aggregate.py)."""
    rows, seen = [], set()
    with open(DATA / "raw" / "bigquery_census.csv") as f:
        for r in csv.DictReader(f):
            if r["url"] in seen:
                continue
            seen.add(r["url"])
            rows.append({"month": f"{r['gkg_date'][:4]}-{r['gkg_date'][4:6]}",
                         "url": r["url"]})
    return rows


def validate_slug_proxy(classified) -> None:
    """Slug-token water hits vs title-token water hits, on rows whose title was
    actually fetched (title_source=live; slug-derived titles would trivially agree)."""
    tp = fp = fn = tn = 0
    matched_slugs = []
    for r in classified:
        if r["title_source"] != "live":
            continue
        slug_hit = bool(url_tokens(r["url"]) & WATER_KW)
        title_hit = bool(tokens(r["title"]) & WATER_KW)
        if slug_hit and title_hit:
            tp += 1
        elif slug_hit:
            fp += 1
            matched_slugs.append((urlparse(r["url"]).path[-70:], r["title"][:70]))
        elif title_hit:
            fn += 1
        else:
            tn += 1
    n = tp + fp + fn + tn
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    print(f"\nSlug-proxy validation (live-title rows, n={n}):")
    print(f"  slug hits {tp + fp}, title hits {tp + fn}, both {tp}")
    print(f"  precision {prec:.2f}  recall {rec:.2f}  agreement {(tp + tn) / n:.4f}")
    if matched_slugs:
        print("  slug-only hits (slug matched, fetched title did not):")
        for path, title in matched_slugs[:20]:
            print(f"    ...{path}  |  {title}")


def build_series(classified, census):
    census_n = Counter()
    water_kw = Counter()
    energy_kw = Counter()
    for r in census:
        census_n[r["month"]] += 1
        tok = url_tokens(r["url"])
        if tok & WATER_KW:
            water_kw[r["month"]] += 1
        if tok & ENERGY_KW:
            energy_kw[r["month"]] += 1

    relevant_n = Counter()
    theme_n = defaultdict(Counter)          # month -> theme counts
    neg_theme_n = defaultdict(Counter)      # month -> theme counts, negative only
    for r in classified:
        if r["relevant"] != "yes":
            continue
        m = r["month"]
        relevant_n[m] += 1
        theme_n[m][r["theme"]] += 1
        if r["sentiment"] == "negative":
            neg_theme_n[m][r["theme"]] += 1

    months = sorted(census_n)
    rows = []
    for m in months:
        cn, rn = census_n[m], relevant_n[m]
        rows.append({
            "month": m,
            "census_n": cn,
            "water_kw_n": water_kw[m],
            "water_kw_share": round(water_kw[m] / cn, 4),
            "energy_kw_n": energy_kw[m],
            "energy_kw_share": round(energy_kw[m] / cn, 4),
            "n_relevant": rn,
            "water_theme_n": theme_n[m]["environment_water"],
            "water_theme_share": round(theme_n[m]["environment_water"] / rn, 4) if rn else 0.0,
            "energy_theme_n": theme_n[m]["energy_grid"],
            "energy_theme_share": round(theme_n[m]["energy_grid"] / rn, 4) if rn else 0.0,
            "water_negative_n": neg_theme_n[m]["environment_water"],
        })
    return rows, neg_theme_n


def to_quarterly(monthly, neg_theme_n):
    q_rows = defaultdict(lambda: Counter())
    for r in monthly:
        q = quarter_of(r["month"])
        for k in ("census_n", "water_kw_n", "energy_kw_n", "n_relevant",
                  "water_theme_n", "energy_theme_n", "water_negative_n"):
            q_rows[q][k] += r[k]
    q_neg = defaultdict(Counter)
    for m, counts in neg_theme_n.items():
        q_neg[quarter_of(m)].update(counts)

    rows = []
    for q in sorted(q_rows):
        c = q_rows[q]
        cn, rn = c["census_n"], c["n_relevant"]
        row = {
            "quarter": q,
            "census_n": cn,
            "water_kw_n": c["water_kw_n"],
            "water_kw_share": round(c["water_kw_n"] / cn, 4),
            "energy_kw_n": c["energy_kw_n"],
            "energy_kw_share": round(c["energy_kw_n"] / cn, 4),
            "n_relevant": rn,
            "water_theme_n": c["water_theme_n"],
            "water_theme_share": round(c["water_theme_n"] / rn, 4) if rn else 0.0,
            "energy_theme_n": c["energy_theme_n"],
            "energy_theme_share": round(c["energy_theme_n"] / rn, 4) if rn else 0.0,
            "water_negative_n": c["water_negative_n"],
        }
        for t in THEMES:
            row[f"neg_{t}"] = q_neg[q][t]
        rows.append(row)
    return rows


def write_csv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {path} ({len(rows)} rows)")


def period_share(monthly, period, num_key, den_key):
    num = sum(r[num_key] for r in monthly if in_period(r["month"], period))
    den = sum(r[den_key] for r in monthly if in_period(r["month"], period))
    return num / den if den else 0.0


def print_summary(monthly, quarterly, neg_theme_n) -> None:
    print("\n=== When did water become mainstream? ===")
    for thresh in (0.05, 0.10):
        hit = None
        for a, b in zip(quarterly, quarterly[1:]):
            if a["water_theme_share"] >= thresh and b["water_theme_share"] >= thresh:
                hit = a["quarter"]
                break
        print(f"  first sustained quarter with water theme >= {thresh:.0%}: "
              f"{hit or 'never (through ' + quarterly[-1]['quarter'] + ')'}")

    print("\n=== Growth: early (2022-2023) vs late (2025-H1 2026) ===")
    for label, num, den in (
            ("water theme (share of relevant)", "water_theme_n", "n_relevant"),
            ("energy theme (share of relevant)", "energy_theme_n", "n_relevant"),
            ("water keyword (share of census)", "water_kw_n", "census_n"),
            ("energy keyword (share of census)", "energy_kw_n", "census_n")):
        e = period_share(monthly, EARLY, num, den)
        l = period_share(monthly, LATE, num, den)
        mult = f"{l / e:.1f}x" if e else "n/a"
        print(f"  {label}: {e:.1%} -> {l:.1%}  ({mult})")

    print("\n=== Theme ranking among negative coverage ===")
    for label, period in (("early 2022-2023", EARLY), ("late 2025-H1 2026", LATE)):
        counts = Counter()
        for m, c in neg_theme_n.items():
            if in_period(m, period):
                counts.update(c)
        total = sum(counts.values())
        ranked = counts.most_common()
        print(f"  {label} (n={total} negative headlines):")
        for i, (t, n) in enumerate(ranked, 1):
            mark = "  <-- water" if t == "environment_water" else ""
            print(f"    {i}. {THEME_LABELS[t]}: {n} ({n / total:.1%}){mark}")


def smooth3(vals):
    return [sum(vals[max(0, i - 1):i + 2]) / len(vals[max(0, i - 1):i + 2])
            for i in range(len(vals))]


def chart_water_vs_energy(monthly, quarterly):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

    q_dates = [quarter_to_date(r["quarter"]) for r in quarterly]
    for key, label, color in (("water_theme_share", "Environment & water", AQUA),
                              ("energy_theme_share", "Energy & grid", BLUE)):
        vals = [100 * r[key] for r in quarterly]
        ax1.plot(q_dates, vals, color=color, linewidth=2)
        ax1.annotate(label, xy=(q_dates[-1], vals[-1]), xytext=(6, 0),
                     textcoords="offset points", fontsize=8.5, color=color,
                     va="center")
    ax1.set_ylabel("Share of relevant headlines", fontsize=9)
    ax1.set_title("Water vs energy in data center coverage",
                  fontsize=13, color=INK, loc="left", pad=14)

    m_dates = [month_to_date(r["month"]) for r in monthly]
    for key, label, color in (("water_kw_share", "Water keywords", AQUA),
                              ("energy_kw_share", "Energy keywords", BLUE)):
        vals = smooth3([100 * r[key] for r in monthly])
        ax2.plot(m_dates, vals, color=color, linewidth=2)
        ax2.annotate(label, xy=(m_dates[-1], vals[-1]), xytext=(6, 0),
                     textcoords="offset points", fontsize=8.5, color=color,
                     va="center")
    ax2.set_ylabel("Share of all census articles", fontsize=9)

    for ax in (ax1, ax2):
        style_axes(ax)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
        ax.set_ylim(bottom=0)
    fig.subplots_adjust(right=0.84)
    fig.text(0.01, 0.015,
             "Top: LLM-classified theme shares, quarterly (n<=150 sampled headlines/month). "
             "Bottom: URL-slug keyword frequency across all 103,341 census articles, 3-mo avg "
             "(water: water/drought/aquifer/groundwater/wastewater; energy: power/energy/"
             "electricity/grid/megawatt/nuclear).",
             fontsize=7.5, color=MUTED)
    fig.savefig(CHARTS / "10_water_vs_energy.png", bbox_inches="tight")
    plt.close(fig)


def chart_backlash_ranking(neg_theme_n):
    periods = []
    for label, period in (("2022-2023", EARLY), ("2025-H1 2026", LATE)):
        counts = Counter()
        for m, c in neg_theme_n.items():
            if in_period(m, period):
                counts.update(c)
        total = sum(counts.values())
        periods.append((label, counts, total))

    order = [t for t, _ in periods[1][1].most_common()]  # sort by late-period share
    order += [t for t in THEMES if t not in order]
    y = list(range(len(order)))[::-1]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    h = 0.36
    for i, (label, counts, total) in enumerate(periods):
        shares = [100 * counts[t] / total for t in order]
        offs = [v + (h / 2 + 0.02 if i == 0 else -h / 2 - 0.02) for v in y]
        colors = [(AQUA if t == "environment_water" else BLUE) if i == 1
                  else "#d9d8d2" for t in order]
        ax.barh(offs, shares, height=h, color=colors, label=label)
        for o, s in zip(offs, shares):
            ax.annotate(f"{s:.0f}%", xy=(s, o), xytext=(4, 0),
                        textcoords="offset points", va="center",
                        fontsize=8, color=INK_2)
    ax.set_yticks(y)
    ax.set_yticklabels([THEME_LABELS[t] for t in order], fontsize=9,
                       color=INK_2)
    style_axes(ax)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.legend(frameon=False, loc="lower right", fontsize=9)
    ax.set_title("What negative data center coverage is about (share of negative headlines)",
                 fontsize=13, color=INK, loc="left", pad=14)
    fig.text(0.01, 0.015,
             "LLM-classified negative-sentiment headlines by theme, early vs late period. "
             "Water highlighted; bars ordered by late-period share.",
             fontsize=7.5, color=MUTED)
    fig.savefig(CHARTS / "11_backlash_theme_ranking.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    classified = load_classified()
    census = load_census()
    validate_slug_proxy(classified)
    monthly, neg_theme_n = build_series(classified, census)
    quarterly = to_quarterly(monthly, neg_theme_n)
    write_csv(DATA / "processed" / "water_deep_dive_monthly.csv", monthly)
    write_csv(DATA / "processed" / "water_deep_dive_quarterly.csv", quarterly)
    chart_water_vs_energy(monthly, quarterly)
    chart_backlash_ranking(neg_theme_n)
    print("Charts written:", CHARTS / "10_water_vs_energy.png",
          "and", CHARTS / "11_backlash_theme_ranking.png")
    print_summary(monthly, quarterly, neg_theme_n)


if __name__ == "__main__":
    main()
