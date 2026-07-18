#!/usr/bin/env python3
"""Fetch a monthly headline pool from GDELT DOC 2.0 using yield-optimized windows.

Design: the artlist endpoint returns at most 250 articles per call, so each call
should carry ~250. For every calendar month (Jan 2022 - Jun 2026) we draw
WINDOWS_PER_MONTH random non-overlapping time windows, each sized (from the known
daily article counts in data/raw/gdelt_daily_volume.csv) to an expected
~TARGET_PER_WINDOW articles - multi-day windows in low-volume months, sub-day
windows in heavy months. One API call per window, 162 calls total.

If a window still hits the 250-record cap the result is kept (slight
end-of-window bias inside that one window) and the event is logged; sampling
150/month from ~700 pooled headlines absorbs this.

Throttle is adaptive: starts at BASE_THROTTLE and stretches when GDELT 429s.
Progress is checkpointed per window; safe to re-run/resume.

Output: data/raw/headlines_pool.jsonl
Checkpoint: data/raw/headlines_progress.txt (window ids)
"""

import csv
import json
import random
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

QUERY = '("data center" OR "data centers" OR "datacenter" OR "datacenters") sourcelang:english'
START_MONTH = (2022, 1)
END_MONTH = (2026, 6)
WINDOWS_PER_MONTH = 3
TARGET_PER_WINDOW = 230
SEED = 20221130  # committed for reproducibility
BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
POOL_PATH = RAW_DIR / "headlines_pool.jsonl"
PROGRESS_PATH = RAW_DIR / "headlines_progress.txt"
BASE_THROTTLE = 75  # GDELT grants roughly one artlist call per ~2 min in practice

throttle = BASE_THROTTLE
calls = 0


def month_range() -> list[tuple[int, int]]:
    months, (y, m) = [], START_MONTH
    while (y, m) <= END_MONTH:
        months.append((y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return months


def build_windows(known: dict[date, int]) -> list[tuple[str, datetime, datetime]]:
    """For each month, WINDOWS_PER_MONTH random non-overlapping windows sized to
    ~TARGET_PER_WINDOW expected articles. Returns (window_id, start, end)."""
    rng = random.Random(SEED)
    windows = []
    for y, m in month_range():
        days = sorted(d for d in known if d.year == y and d.month == m and known[d] > 0)
        used: set[date] = set()
        for w in range(WINDOWS_PER_MONTH):
            candidates = [d for d in days if d not in used]
            if not candidates:
                break
            start_day = rng.choice(candidates)
            count = known[start_day]
            if count >= TARGET_PER_WINDOW:
                # sub-day window: hours sized to expected target, random offset
                hours = max(1, int(24 * TARGET_PER_WINDOW / count))
                offset = rng.randrange(0, 24 - hours + 1)
                start = datetime(start_day.year, start_day.month, start_day.day, offset)
                end = start + timedelta(hours=hours)
                used.add(start_day)
            else:
                # extend forward across days until ~target expected
                span = [start_day]
                total = count
                nxt = start_day + timedelta(days=1)
                while total < TARGET_PER_WINDOW and nxt in known and nxt not in used \
                        and nxt.month == m and known[nxt] > 0 \
                        and total + known[nxt] <= 250:
                    span.append(nxt)
                    total += known[nxt]
                    nxt += timedelta(days=1)
                used.update(span)
                start = datetime(span[0].year, span[0].month, span[0].day)
                end = datetime(span[-1].year, span[-1].month, span[-1].day) + timedelta(days=1)
            windows.append((f"{y:04d}-{m:02d}-w{w}", start, end))
    return windows


def gdelt_artlist(start_dt: datetime, end_dt: datetime) -> list[dict]:
    """GDELT rejects in long walls (sustained 429) between grace bursts, and every
    rejected request appears to refresh the penalty. So: short spacing while calls
    succeed, and long SILENT sleeps (15 -> 60 min) once a wall is hit. Never gives up."""
    global calls, throttle
    params = {
        "query": QUERY,
        "mode": "artlist",
        "maxrecords": 250,
        "sort": "datedesc",
        "startdatetime": start_dt.strftime("%Y%m%d%H%M%S"),
        "enddatetime": end_dt.strftime("%Y%m%d%H%M%S"),
        "format": "json",
    }
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "User-Agent": "datacenter-media-sentiment research (github open-data project)"})
    attempt = 0
    while True:
        time.sleep(throttle)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            data = json.loads(body)  # rate-limit text page raises JSONDecodeError
            calls += 1
            throttle = max(BASE_THROTTLE, throttle * 0.9)
            return data.get("articles", [])
        except (json.JSONDecodeError, OSError) as e:  # OSError covers URLError, SSL, DNS, timeouts
            attempt += 1
            if attempt <= 2:
                wait = 90  # brief blip: retry soon
            else:
                wait = min(900 * (attempt - 2), 3600)  # wall: back off silently
            print(f"  attempt {attempt} failed ({e}); sleeping {wait / 60:.0f}m",
                  flush=True)
            time.sleep(wait)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    known = {}
    with open(RAW_DIR / "gdelt_daily_volume.csv") as f:
        for r in csv.DictReader(f):
            known[date.fromisoformat(r["date"])] = int(r["article_count"])

    windows = build_windows(known)
    print(f"Plan: {len(windows)} windows across {len(month_range())} months "
          f"(seed={SEED}, {WINDOWS_PER_MONTH}/month, ~{TARGET_PER_WINDOW}/window)", flush=True)

    done = set()
    if PROGRESS_PATH.exists():
        done = set(PROGRESS_PATH.read_text().split())
        print(f"Resuming: {len(done)} windows already done", flush=True)

    with open(POOL_PATH, "a") as pool, open(PROGRESS_PATH, "a") as progress:
        for n, (wid, start, end) in enumerate(windows, 1):
            if wid in done:
                continue
            articles = gdelt_artlist(start, end)
            capped = " CAP-HIT" if len(articles) >= 250 else ""
            for a in articles:
                pool.write(json.dumps({
                    "window": wid,
                    "seendate": a.get("seendate", ""),
                    "title": a.get("title", ""),
                    "url": a.get("url", ""),
                    "domain": a.get("domain", ""),
                    "sourcecountry": a.get("sourcecountry", ""),
                    "language": a.get("language", ""),
                }, ensure_ascii=False) + "\n")
            pool.flush()
            progress.write(wid + "\n")
            progress.flush()
            print(f"{wid} {start:%Y-%m-%d %H:%M}..{end:%m-%d %H:%M} got={len(articles)}{capped} "
                  f"[{n}/{len(windows)}, {calls} calls]", flush=True)

    print(f"DONE: {calls} API calls", flush=True)


if __name__ == "__main__":
    main()
