#!/usr/bin/env python3
"""Aggregate daily GDELT series and classified headlines into monthly datasets.

Inputs:
  data/raw/gdelt_daily_volume.csv
  data/raw/gdelt_daily_tone.csv
  data/processed/headlines_classified.csv   (from the LLM classification step)

Outputs:
  data/processed/monthly_volume.csv    month, article_count, days_with_data,
                                       avg_daily_volume_pct, avg_tone
  data/processed/monthly_sentiment.csv month, n_sampled, n_relevant, sentiment shares,
                                       net_sentiment, theme shares

Notes: avg_tone is weighted by daily article count (population mean over articles,
not over days). Months with missing days (GDELT outages: 2023-03-23 and
2025-06-15..2025-07-01) report days_with_data < calendar days; volume_pct is
per-day normalized so those months remain comparable on that metric.
"""

import csv
from collections import Counter, defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
THEMES = ["energy_grid", "environment_water", "community_opposition",
          "investment_buildout", "jobs_economy", "policy_regulation",
          "tech_operations", "other"]


def monthly_volume() -> None:
    counts = defaultdict(int)
    days = defaultdict(int)
    pct = defaultdict(list)
    with open(DATA / "raw" / "gdelt_daily_volume.csv") as f:
        for r in csv.DictReader(f):
            m = r["date"][:7]
            counts[m] += int(r["article_count"])
            days[m] += 1
            pct[m].append(float(r["volume_pct"]))

    tone_num = defaultdict(float)
    day_count = {}
    with open(DATA / "raw" / "gdelt_daily_volume.csv") as f:
        for r in csv.DictReader(f):
            day_count[r["date"]] = int(r["article_count"])
    with open(DATA / "raw" / "gdelt_daily_tone.csv") as f:
        for r in csv.DictReader(f):
            m = r["date"][:7]
            tone_num[m] += float(r["avg_tone"]) * day_count.get(r["date"], 0)

    out = DATA / "processed" / "monthly_volume.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["month", "article_count", "days_with_data",
                    "avg_daily_volume_pct", "avg_tone"])
        for m in sorted(counts):
            w.writerow([m, counts[m], days[m],
                        round(sum(pct[m]) / len(pct[m]), 6),
                        round(tone_num[m] / counts[m], 4) if counts[m] else ""])
    print(f"Wrote {out} ({len(counts)} months)")


def monthly_headline_census() -> None:
    """Monthly article count and mean tone over the headline-frame census
    (data/raw/bigquery_census.csv, deduped by URL)."""
    path = DATA / "raw" / "bigquery_census.csv"
    if not path.exists():
        print("Skipping headline census aggregation (bigquery_census.csv not found)")
        return
    seen = set()
    count = defaultdict(int)
    tone_sum = defaultdict(float)
    with open(path) as f:
        for r in csv.DictReader(f):
            if r["url"] in seen:
                continue
            seen.add(r["url"])
            m = f"{r['gkg_date'][:4]}-{r['gkg_date'][4:6]}"
            count[m] += 1
            tone_sum[m] += float(r["tone"])
    out = DATA / "processed" / "monthly_headline_census.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["month", "article_count", "avg_tone"])
        for m in sorted(count):
            w.writerow([m, count[m], round(tone_sum[m] / count[m], 4)])
    print(f"Wrote {out} ({len(count)} months)")


def monthly_sentiment() -> None:
    path = DATA / "processed" / "census_classified.csv"
    if not path.exists():
        print(f"Skipping sentiment aggregation ({path} not found yet)")
        return
    sampled = Counter()
    sent = defaultdict(Counter)
    theme = defaultdict(Counter)
    with open(path) as f:
        for r in csv.DictReader(f):
            m = r["month"]
            sampled[m] += 1
            if r["relevant"] == "yes":
                sent[m][r["sentiment"]] += 1
                theme[m][r["theme"]] += 1

    out = DATA / "processed" / "monthly_sentiment.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["month", "n_sampled", "n_relevant",
                    "positive_share", "negative_share", "neutral_share",
                    "net_sentiment"] + [f"theme_{t}" for t in THEMES])
        for m in sorted(sampled):
            n_rel = sum(sent[m].values())
            if n_rel:
                pos = sent[m]["positive"] / n_rel
                neg = sent[m]["negative"] / n_rel
                neu = sent[m]["neutral"] / n_rel
            else:
                pos = neg = neu = 0.0
            row = [m, sampled[m], n_rel,
                   round(pos, 4), round(neg, 4), round(neu, 4), round(pos - neg, 4)]
            row += [round(theme[m][t] / n_rel, 4) if n_rel else 0.0 for t in THEMES]
            w.writerow(row)
    print(f"Wrote {out} ({len(sampled)} months)")


if __name__ == "__main__":
    monthly_volume()
    monthly_headline_census()
    monthly_sentiment()
