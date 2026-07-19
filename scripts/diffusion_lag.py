#!/usr/bin/env python3
"""Local-vs-national diffusion lag: does local-outlet negativity lead national?

Joins the classified headline sample (census_classified.csv) to LLM-classified
outlet types (domain_types.csv), builds monthly + quarterly sentiment series per
outlet bucket (local / national / trade; wire_pr and other excluded from the lag
test), and cross-correlates local vs national negative shares at a range of
leads/lags. Significance via exhaustive circular-shift null (no scipy; with N
points there are N-1 distinct shifts, so p-value granularity is 1/(N-1)).

Inputs:
  data/processed/census_classified.csv
  data/processed/domain_types.csv        (from classify_domains.py)

Outputs:
  data/processed/diffusion_monthly.csv
  data/processed/diffusion_quarterly.csv
  charts/12_local_vs_national.png
  Summary stats printed to stdout.
"""

import csv
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CHARTS = ROOT / "charts"

BUCKETS = ["local", "national", "trade"]

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

BUCKET_COLORS = {"local": RED, "national": BLUE, "trade": YELLOW}

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


def style_axes(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def smooth3(vals):
    return [sum(vals[max(0, i - 1):i + 2]) / len(vals[max(0, i - 1):i + 2])
            for i in range(len(vals))]


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return sxy / (sxx * syy) ** 0.5 if sxx and syy else 0.0


def corr_at_lag(local, national, k):
    """corr(local[t], national[t+k]); k>0 means local leads national by k."""
    if k >= 0:
        xs, ys = local[:len(local) - k or None], national[k:]
    else:
        xs, ys = local[-k:], national[:len(national) + k or None]
    return pearson(xs, ys)


def shift_pvalue(local, national, k):
    """Share of circular shifts of `national` with |corr at lag k| >= observed."""
    obs = abs(corr_at_lag(local, national, k))
    n = len(national)
    hits = sum(abs(corr_at_lag(local, national[s:] + national[:s], k)) >= obs - 1e-12
               for s in range(1, n))
    return hits / (n - 1)


def load_buckets():
    types = {}
    with open(DATA / "processed" / "domain_types.csv") as f:
        for r in csv.DictReader(f):
            types[r["domain"]] = r["outlet_type"]
    rows = []
    unmapped = Counter()
    excluded = Counter()
    with open(DATA / "processed" / "census_classified.csv") as f:
        for r in csv.DictReader(f):
            if r["relevant"] != "yes":
                continue
            d = r["domain"].split(":")[0]
            t = types.get(d)
            if t is None:
                unmapped[d] += 1
                continue
            if t not in BUCKETS:
                excluded[t] += 1
                continue
            rows.append({"month": r["month"], "bucket": t,
                         "sentiment": r["sentiment"]})
    if unmapped:
        print(f"WARNING: {sum(unmapped.values())} relevant rows with unmapped "
              f"domains: {dict(unmapped.most_common(5))}")
    print(f"Bucketed relevant rows: {len(rows)}; excluded "
          f"{dict(excluded)} (wire/PR and other outlets)")
    return rows


def build_series(rows, key_fn):
    n = defaultdict(Counter)
    neg = defaultdict(Counter)
    pos = defaultdict(Counter)
    for r in rows:
        k = key_fn(r["month"])
        n[k][r["bucket"]] += 1
        if r["sentiment"] == "negative":
            neg[k][r["bucket"]] += 1
        elif r["sentiment"] == "positive":
            pos[k][r["bucket"]] += 1
    out = []
    for k in sorted(n):
        row = {"period": k}
        for b in BUCKETS:
            nb = n[k][b]
            row[f"{b}_n"] = nb
            row[f"{b}_negative_share"] = round(neg[k][b] / nb, 4) if nb else ""
            row[f"{b}_net_sentiment"] = (
                round((pos[k][b] - neg[k][b]) / nb, 4) if nb else "")
        out.append(row)
    return out


def write_csv(path, rows, period_name):
    with open(path, "w", newline="") as f:
        fields = [period_name] + [k for k in rows[0] if k != "period"]
        w = csv.writer(f)
        w.writerow(fields)
        for r in rows:
            w.writerow([r["period"]] + [r[k] for k in fields[1:]])
    print(f"Wrote {path} ({len(rows)} rows)")


def first_sustained_flip(series):
    """First period with net sentiment < 0 in this and the following period."""
    for a, b in zip(series, series[1:]):
        if a[1] < 0 and b[1] < 0:
            return a[0]
    return None


def lag_analysis(quarterly, monthly):
    q_local = [r["local_negative_share"] for r in quarterly]
    q_natl = [r["national_negative_share"] for r in quarterly]
    print("\n=== Quarterly cross-correlation: local vs national negative share ===")
    print("  (positive lag = local leads national by that many quarters)")
    q_curve = []
    for k in range(-3, 4):
        c = corr_at_lag(q_local, q_natl, k)
        p = shift_pvalue(q_local, q_natl, k)
        q_curve.append((k, c, p))
        print(f"  lag {k:+d}: r = {c:+.2f}  (circular-shift p = {p:.2f})")
    best = max(q_curve, key=lambda t: t[1])
    print(f"  best lag: {best[0]:+d} quarters (r = {best[1]:+.2f}, p = {best[2]:.2f})")

    m_local = smooth3([r["local_negative_share"] for r in monthly])
    m_natl = smooth3([r["national_negative_share"] for r in monthly])
    print("\n=== Monthly (3-mo smoothed) cross-correlation, lags -6..+6 months ===")
    m_curve = [(k, corr_at_lag(m_local, m_natl, k),
                shift_pvalue(m_local, m_natl, k)) for k in range(-6, 7)]
    for k, c, p in m_curve:
        print(f"  lag {k:+d}: r = {c:+.2f}  (p = {p:.2f})")
    m_best = max(m_curve, key=lambda t: t[1])
    print(f"  best lag: {m_best[0]:+d} months (r = {m_best[1]:+.2f}, p = {m_best[2]:.2f})")
    return q_curve


def chart(quarterly, q_curve):
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(10, 7.5), height_ratios=[3, 2])

    q_dates = [quarter_to_date(r["period"]) for r in quarterly]
    label_nudge = {"national": -4, "trade": 4}
    for b in BUCKETS:
        vals = [100 * r[f"{b}_negative_share"] for r in quarterly]
        ax1.plot(q_dates, vals, color=BUCKET_COLORS[b], linewidth=2)
        ax1.annotate(b.capitalize(), xy=(q_dates[-1], vals[-1]),
                     xytext=(6, label_nudge.get(b, 0)),
                     textcoords="offset points",
                     fontsize=8.5, color=BUCKET_COLORS[b], va="center")
        flip = first_sustained_flip(
            [(r["period"], r[f"{b}_net_sentiment"]) for r in quarterly])
        if flip:
            i = [r["period"] for r in quarterly].index(flip)
            ax1.plot([q_dates[i]], [vals[i]], "o", color=BUCKET_COLORS[b],
                     markersize=6)
            ax1.annotate(f"net flip {flip}", xy=(q_dates[i], vals[i]),
                         xytext=(0, 10), textcoords="offset points",
                         ha="center", fontsize=7.5, color=BUCKET_COLORS[b])
    style_axes(ax1)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax1.set_ylabel("Negative share of relevant headlines", fontsize=9)
    ax1.set_title("Local outlets are the most negative on data centers - and the only ones net-negative",
                  fontsize=13, color=INK, loc="left", pad=14)

    lags = [k for k, _, _ in q_curve]
    corrs = [c for _, c, _ in q_curve]
    best_k = max(q_curve, key=lambda t: t[1])[0]
    colors = [RED if k == best_k else BLUE_LIGHT for k in lags]
    ax2.bar(lags, corrs, color=colors, width=0.6)
    ax2.axhline(0, color=AXIS, linewidth=1)
    style_axes(ax2)
    ax2.set_xticks(lags)
    ax2.set_xlabel("Lag in quarters (positive = local leads national)", fontsize=9)
    ax2.set_ylabel("Correlation of negative shares", fontsize=9)

    fig.text(0.01, 0.015,
             "Quarterly negative-share series by LLM-classified outlet type; dots mark first sustained "
             "net-negative quarter. Bottom: Pearson cross-correlation of local vs national negative share; "
             "best lag highlighted. Wire/PR and unclassifiable outlets excluded.",
             fontsize=7.5, color=MUTED)
    fig.savefig(CHARTS / "12_local_vs_national.png", bbox_inches="tight")
    plt.close(fig)
    print("Wrote", CHARTS / "12_local_vs_national.png")


def main() -> None:
    rows = load_buckets()
    monthly = build_series(rows, lambda m: m)
    quarterly = build_series(rows, quarter_of)
    write_csv(DATA / "processed" / "diffusion_monthly.csv", monthly, "month")
    write_csv(DATA / "processed" / "diffusion_quarterly.csv", quarterly, "quarter")

    print("\n=== Bucket sizes ===")
    for b in BUCKETS:
        total = sum(r[f"{b}_n"] for r in quarterly)
        qs = [r[f"{b}_n"] for r in quarterly]
        print(f"  {b}: {total} rows ({min(qs)}-{max(qs)}/quarter)")
    print("  Caveat: shares from small quarterly samples carry sampling error "
          "of roughly +/-1/sqrt(n); treat sub-10pp differences accordingly.")

    print("\n=== First sustained net-negative quarter (this and next < 0) ===")
    for b in BUCKETS:
        flip = first_sustained_flip(
            [(r["period"], r[f"{b}_net_sentiment"]) for r in quarterly])
        print(f"  {b}: {flip or 'none through ' + quarterly[-1]['period']}")

    q_curve = lag_analysis(quarterly, monthly)
    chart(quarterly, q_curve)


if __name__ == "__main__":
    main()
