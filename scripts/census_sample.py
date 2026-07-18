#!/usr/bin/env python3
"""Draw the monthly candidate sample from the BigQuery census and recover headlines.

Frame: articles whose URL path mentions data center terms (headline-frame census,
data/raw/bigquery_census.csv, from GDELT GKG via BigQuery - see README).

For each month: dedupe URLs, draw 180 seeded-random candidates in a deterministic
order, fetch each page's real title (og:title preferred, <title> fallback), fall
back to URL-slug-derived text when the page is gone, and keep the first 150
candidates with a usable headline.

Output: data/raw/census_sample.csv
        (id, month, gkg_date, url, domain, title, title_source)
"""

import concurrent.futures
import csv
import gzip
import html
import io
import random
import re
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

SEED = 20221130
CANDIDATES_PER_MONTH = 180
TARGET_PER_MONTH = 150
ROOT = Path(__file__).resolve().parent.parent
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

TITLE_RE = re.compile(
    rb'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']{5,300})["\']|'
    rb'<meta[^>]+content=["\']([^"\']{5,300})["\'][^>]+property=["\']og:title["\']|'
    rb'<title[^>]*>([^<]{5,300})</title>', re.I)


def fetch_title(url: str) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Encoding": "gzip"})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            raw = resp.read(131072)
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read(131072)
    except Exception:
        return None
    m = TITLE_RE.search(raw)
    if not m:
        return None
    title = next(g for g in m.groups() if g)
    try:
        text = html.unescape(title.decode("utf-8", errors="replace")).strip()
    except Exception:
        return None
    return text if len(text) >= 5 else None


def slug_title(url: str) -> str | None:
    path = urllib.parse.unquote(urllib.parse.urlparse(url).path)
    path = re.sub(r"[^\x20-\x7e]", "", path)  # drop non-ascii remnants
    seg = max((s for s in path.split("/") if s), key=len, default="")
    seg = re.sub(r"\.(html?|php|aspx?|cfm)$", "", seg)
    tokens = [t for t in re.split(r"[-_]+", seg)
              if re.search(r"[a-zA-Z]{2}", t) and not re.fullmatch(r"[0-9a-f]{6,}", t)]
    if len(tokens) < 4:
        return None
    return " ".join(tokens)


def main() -> None:
    by_month = defaultdict(list)
    seen = set()
    with open(ROOT / "data/raw/bigquery_census.csv") as f:
        for r in csv.DictReader(f):
            if r["url"] in seen:
                continue
            seen.add(r["url"])
            month = f"{r['gkg_date'][:4]}-{r['gkg_date'][4:6]}"
            by_month[month].append(r)

    candidates = []
    for month in sorted(by_month):
        rows = sorted(by_month[month], key=lambda x: (x["gkg_date"], x["url"]))
        rng = random.Random(f"{SEED}-{month}")
        k = min(CANDIDATES_PER_MONTH, len(rows))
        candidates.extend((month, r) for r in rng.sample(rows, k))

    print(f"Fetching titles for {len(candidates)} candidate urls...", flush=True)
    titles = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(fetch_title, r["url"]): r["url"] for _, r in candidates}
        for n, fut in enumerate(concurrent.futures.as_completed(futs), 1):
            titles[futs[fut]] = fut.result()
            if n % 500 == 0:
                print(f"  {n}/{len(candidates)} fetched", flush=True)

    out_rows = []
    per_month = defaultdict(int)
    stats = defaultdict(int)
    for month, r in candidates:
        if per_month[month] >= TARGET_PER_MONTH:
            continue
        live = titles.get(r["url"])
        if live:
            title, source = live, "live"
        else:
            title, source = (slug_title(r["url"]), "slug")
            if not title:
                stats["unusable"] += 1
                continue
        stats[source] += 1
        per_month[month] += 1
        domain = urllib.parse.urlparse(r["url"]).netloc.removeprefix("www.")
        out_rows.append([month, r["gkg_date"], r["url"], domain, title, source])

    out = ROOT / "data/raw/census_sample.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "month", "gkg_date", "url", "domain", "title", "title_source"])
        for i, row in enumerate(out_rows, 1):
            w.writerow([i] + row)

    print(f"\nWrote {len(out_rows)} rows -> {out}")
    print(f"titles: {stats['live']} live, {stats['slug']} slug-derived, "
          f"{stats['unusable']} unusable/skipped")
    short = {m: c for m, c in per_month.items() if c < TARGET_PER_MONTH}
    if short:
        print("months under target:", short)


if __name__ == "__main__":
    main()
