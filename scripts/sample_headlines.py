#!/usr/bin/env python3
"""Draw the monthly headline sample for LLM sentiment classification.

Reads data/raw/headlines_pool.jsonl (complete article pulls for 8 random days per
month), dedupes, and draws up to SAMPLE_PER_MONTH headlines per calendar month with
a seeded RNG so the sample is exactly reproducible.

Dedupe: exact URL, then normalized title within a month (syndicated wire copies of
the same story otherwise dominate a month's sample).

Output: data/raw/headlines_sample.csv
"""

import csv
import json
import random
import re
from collections import defaultdict
from pathlib import Path

SAMPLE_PER_MONTH = 150
SEED = 20221130  # same committed seed as fetch_headlines.py
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def norm_title(title: str) -> str:
    t = title.lower()
    t = re.sub(r"\s*[-|–—]\s*[^-|–—]{0,40}$", "", t)  # trailing "- Outlet"
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def complete_months() -> set:
    """Months whose 3 fetch windows are all checkpointed as done."""
    done = set((RAW_DIR / "headlines_progress.txt").read_text().split())
    return {m for m in {w.rsplit("-w", 1)[0] for w in done}
            if all(f"{m}-w{i}" in done for i in range(3))}


def main() -> None:
    finished = complete_months()
    by_month = defaultdict(list)
    seen_urls = set()
    n_raw = 0
    with open(RAW_DIR / "headlines_pool.jsonl") as f:
        for line in f:
            a = json.loads(line)
            n_raw += 1
            if not a["title"] or not a["seendate"]:
                continue
            if a["url"] in seen_urls:
                continue
            seen_urls.add(a["url"])
            month = f"{a['seendate'][:4]}-{a['seendate'][4:6]}"
            if month in finished:
                by_month[month].append(a)

    out_rows = []
    for month in sorted(by_month):
        # per-month RNG: each month's sample is independent of other months,
        # so completed months are stable while the pool is still growing
        rng = random.Random(f"{SEED}-{month}")
        titles_seen = set()
        unique = []
        for a in sorted(by_month[month], key=lambda x: (x["seendate"], x["url"])):
            key = norm_title(a["title"])
            if key and key not in titles_seen:
                titles_seen.add(key)
                unique.append(a)
        k = min(SAMPLE_PER_MONTH, len(unique))
        sample = rng.sample(unique, k)
        sample.sort(key=lambda x: (x["seendate"], x["url"]))
        for a in sample:
            out_rows.append(a)
        flag = "" if k == SAMPLE_PER_MONTH else "  <-- UNDER TARGET"
        print(f"{month}: pool={len(by_month[month])} unique={len(unique)} sampled={k}{flag}")

    out_path = RAW_DIR / "headlines_sample.csv"
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "month", "seendate", "title", "url", "domain", "sourcecountry"])
        for i, a in enumerate(out_rows, 1):
            month = f"{a['seendate'][:4]}-{a['seendate'][4:6]}"
            w.writerow([i, month, a["seendate"], a["title"], a["url"],
                        a["domain"], a["sourcecountry"]])
    print(f"\nWrote {len(out_rows)} rows ({n_raw} raw pool lines) -> {out_path}")


if __name__ == "__main__":
    main()
