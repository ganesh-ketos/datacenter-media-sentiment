#!/usr/bin/env python3
"""Calibration of LLM headline sentiment against GDELT lexicon tone.

For each technology, Pearson correlation between the LLM net-sentiment series
and the (article-count-weighted) GDELT tone series over the same periods.
Datacenter is computed monthly and quarterly from the main-study series; the
five comparison technologies have quarterly LLM series, so tone is aggregated
to quarters (weighted by article count) before correlating.

Inputs:
  data/processed/monthly_sentiment.csv          (datacenter LLM, monthly)
  data/processed/monthly_headline_census.csv    (datacenter tone, monthly)
  data/processed/comparison_quarterly_sentiment.csv  (5 topics, LLM, quarterly)
  data/processed/comparison_monthly.csv         (5 topics, tone, monthly)

Output:
  data/processed/calibration.csv   topic, grain, n_periods, pearson_r
"""

import csv
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return sxy / (sxx * syy) ** 0.5 if sxx and syy else float("nan")


def quarter_of(month: str) -> str:
    y, m = month.split("-")
    return f"{y}Q{(int(m) - 1) // 3 + 1}"


def datacenter_series():
    sent = {r["month"]: (float(r["net_sentiment"]), int(r["n_relevant"]))
            for r in csv.DictReader(open(DATA / "processed" / "monthly_sentiment.csv"))}
    tone = {r["month"]: (float(r["avg_tone"]), int(r["article_count"]))
            for r in csv.DictReader(open(DATA / "processed" / "monthly_headline_census.csv"))}
    months = sorted(set(sent) & set(tone))
    monthly = [(sent[m][0], tone[m][0]) for m in months]

    q_sent = defaultdict(lambda: [0.0, 0])
    q_tone = defaultdict(lambda: [0.0, 0])
    for m in months:
        q = quarter_of(m)
        s, n = sent[m]
        q_sent[q][0] += s * n
        q_sent[q][1] += n
        t, c = tone[m]
        q_tone[q][0] += t * c
        q_tone[q][1] += c
    quarterly = [(q_sent[q][0] / q_sent[q][1], q_tone[q][0] / q_tone[q][1])
                 for q in sorted(q_sent)]
    return monthly, quarterly


def comparison_series():
    sent = defaultdict(dict)
    for r in csv.DictReader(open(DATA / "processed" / "comparison_quarterly_sentiment.csv")):
        sent[r["topic"]][r["quarter"]] = float(r["net_sentiment"])
    tone = defaultdict(lambda: defaultdict(lambda: [0.0, 0]))
    for r in csv.DictReader(open(DATA / "processed" / "comparison_monthly.csv")):
        q = quarter_of(r["month"])
        c = int(r["article_count"])
        tone[r["topic"]][q][0] += float(r["avg_tone"]) * c
        tone[r["topic"]][q][1] += c
    out = {}
    for topic in sent:
        quarters = sorted(set(sent[topic]) & set(tone[topic]))
        out[topic] = [(sent[topic][q], tone[topic][q][0] / tone[topic][q][1])
                      for q in quarters]
    return out


def main() -> None:
    rows = []
    monthly, quarterly = datacenter_series()
    rows.append(["datacenter", "monthly", len(monthly),
                 round(pearson(*zip(*monthly)), 4)])
    rows.append(["datacenter", "quarterly", len(quarterly),
                 round(pearson(*zip(*quarterly)), 4)])
    for topic, series in sorted(comparison_series().items()):
        rows.append([topic, "quarterly", len(series),
                     round(pearson(*zip(*series)), 4)])

    out = DATA / "processed" / "calibration.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["topic", "grain", "n_periods", "pearson_r"])
        w.writerows(rows)
    print(f"Wrote {out}")
    for r in rows:
        print(f"  {r[0]:<14} {r[1]:<10} n={r[2]:<4} r={r[3]:+.4f}")


if __name__ == "__main__":
    main()
