#!/usr/bin/env python3
"""Merge per-batch classification part files into headlines_classified.csv.

Used when classification is run as parallel LLM batches writing
data/processed/parts/part_*.csv (id,relevant,sentiment,theme). Validates that
ids exactly cover the sample, values are legal, then joins with
data/raw/headlines_sample.csv metadata.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARTS = ROOT / "data" / "processed" / "parts"
THEMES = {"energy_grid", "environment_water", "community_opposition",
          "investment_buildout", "jobs_economy", "policy_regulation",
          "tech_operations", "other"}


def main() -> None:
    with open(ROOT / "data/raw/headlines_sample.csv") as f:
        sample = {int(r["id"]): r for r in csv.DictReader(f)}

    labels = {}
    for part in sorted(PARTS.glob("part_*.csv")):
        with open(part) as f:
            for r in csv.DictReader(f):
                i = int(r["id"])
                assert i not in labels, f"duplicate id {i} in {part.name}"
                assert r["relevant"] in {"yes", "no"}, (part.name, r)
                assert r["sentiment"] in {"positive", "negative", "neutral"}, (part.name, r)
                assert r["theme"] in THEMES, (part.name, r)
                labels[i] = r

    classified = sorted(set(labels) & set(sample))
    missing = sorted(set(sample) - set(labels))
    extra = sorted(set(labels) - set(sample))
    assert not extra, f"labels for unknown ids: {extra[:10]}"
    if missing:
        print(f"note: {len(missing)} sampled ids not yet classified "
              f"(first: {missing[:5]}) - writing the {len(classified)} done")

    out = ROOT / "data/processed/headlines_classified.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "month", "seendate", "title", "domain",
                    "sourcecountry", "relevant", "sentiment", "theme"])
        for i in classified:
            s, c = sample[i], labels[i]
            w.writerow([i, s["month"], s["seendate"], s["title"], s["domain"],
                        s["sourcecountry"], c["relevant"], c["sentiment"], c["theme"]])
    print(f"Wrote {len(classified)} classified headlines -> {out}")


if __name__ == "__main__":
    main()
