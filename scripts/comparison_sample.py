#!/usr/bin/env python3
"""Draw quarterly validation samples for the comparison technologies.

For each of the five comparison topics (fracking, wind, solar, 5g, crypto_mining)
and each quarter 2015Q2-2026Q2, draw up to 48 seeded-random candidate articles
from data/raw/cross_industry_comparison.csv, recover headlines (live page title,
URL-slug fallback), and keep the first 40 usable per topic-quarter.

These samples validate GDELT tone as a cross-technology sentiment instrument via
LLM classification; the datacenter series keeps its own monthly 150/month sample.

Output: data/raw/comparison_sample.csv
        (id, topic, quarter, gkg_date, url, domain, title, title_source)
"""

import concurrent.futures
import csv
import random
import urllib.parse
from collections import defaultdict
from pathlib import Path

from census_sample import fetch_title, slug_title

SEED = 20221130
CANDIDATES = 48
TARGET = 40
TOPICS = ["fracking", "wind", "solar", "5g", "crypto_mining"]
ROOT = Path(__file__).resolve().parent.parent


def quarter(gkg_date: str) -> str:
    y, m = int(gkg_date[:4]), int(gkg_date[4:6])
    return f"{y}Q{(m - 1) // 3 + 1}"


def main() -> None:
    pools = defaultdict(list)
    seen = set()
    with open(ROOT / "data/raw/cross_industry_comparison.csv") as f:
        for r in csv.DictReader(f):
            if r["topic"] not in TOPICS or r["url"] in seen:
                continue
            seen.add(r["url"])
            pools[(r["topic"], quarter(r["gkg_date"]))].append(r)

    candidates = []
    for key in sorted(pools):
        rows = sorted(pools[key], key=lambda x: (x["gkg_date"], x["url"]))
        rng = random.Random(f"{SEED}-{key[0]}-{key[1]}")
        candidates.extend((key, r) for r in rng.sample(rows, min(CANDIDATES, len(rows))))

    print(f"Fetching titles for {len(candidates)} candidate urls...", flush=True)
    titles = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(fetch_title, r["url"]): r["url"] for _, r in candidates}
        for n, fut in enumerate(concurrent.futures.as_completed(futs), 1):
            titles[futs[fut]] = fut.result()
            if n % 1000 == 0:
                print(f"  {n}/{len(candidates)} fetched", flush=True)

    out_rows = []
    per_key = defaultdict(int)
    for (topic, q), r in candidates:
        if per_key[(topic, q)] >= TARGET:
            continue
        live = titles.get(r["url"])
        title, source = (live, "live") if live else (slug_title(r["url"]), "slug")
        if not title:
            continue
        per_key[(topic, q)] += 1
        domain = urllib.parse.urlparse(r["url"]).netloc.removeprefix("www.")
        out_rows.append([topic, q, r["gkg_date"], r["url"], domain, title, source])

    out = ROOT / "data/raw/comparison_sample.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "topic", "quarter", "gkg_date", "url", "domain",
                    "title", "title_source"])
        for i, row in enumerate(out_rows, 1):
            w.writerow([i] + row)
    short = {k: v for k, v in per_key.items() if v < TARGET}
    print(f"Wrote {len(out_rows)} rows -> {out}")
    print(f"topic-quarters under target ({TARGET}): {len(short)}")


if __name__ == "__main__":
    main()
