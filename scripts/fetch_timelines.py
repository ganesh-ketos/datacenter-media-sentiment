#!/usr/bin/env python3
"""Fetch daily article volume and tone for datacenter coverage from the GDELT DOC 2.0 API.

Outputs:
  data/raw/gdelt_daily_volume.csv  (date, article_count, total_monitored, volume_pct)
  data/raw/gdelt_daily_tone.csv    (date, avg_tone)

GDELT DOC 2.0 API: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
Rate limit: 1 request / 5 seconds (we wait 6s between calls).
"""

import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

QUERY = '("data center" OR "data centers" OR "datacenter" OR "datacenters") sourcelang:english'
START = "20220101000000"
END = "20260630235959"
BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
THROTTLE_SECONDS = 6


def gdelt_get(params: dict) -> dict:
    url = BASE + "?" + urllib.parse.urlencode(params)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body)
        except (json.JSONDecodeError, urllib.error.HTTPError, urllib.error.URLError) as e:
            wait = 15 * (attempt + 1)
            print(f"  retry {attempt + 1} after error: {e} (waiting {wait}s)", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"GDELT request failed after 5 attempts: {url}")


def fetch_timeline(mode: str) -> list[dict]:
    print(f"Fetching mode={mode} {START}..{END}")
    data = gdelt_get(
        {
            "query": QUERY,
            "mode": mode,
            "startdatetime": START,
            "enddatetime": END,
            "format": "json",
        }
    )
    series = data["timeline"][0]["data"]
    print(f"  got {len(series)} daily points ({series[0]['date'][:8]}..{series[-1]['date'][:8]})")
    return series


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    vol = fetch_timeline("timelinevolraw")
    time.sleep(THROTTLE_SECONDS)
    tone = fetch_timeline("timelinetone")

    with open(OUT_DIR / "gdelt_daily_volume.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "article_count", "total_monitored", "volume_pct"])
        for p in vol:
            date = p["date"][:8]
            count = p["value"]
            norm = p.get("norm", 0)
            pct = round(100.0 * count / norm, 6) if norm else ""
            w.writerow([f"{date[:4]}-{date[4:6]}-{date[6:8]}", count, norm, pct])

    with open(OUT_DIR / "gdelt_daily_tone.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "avg_tone"])
        for p in tone:
            date = p["date"][:8]
            w.writerow([f"{date[:4]}-{date[4:6]}-{date[6:8]}", p["value"]])

    print("Wrote gdelt_daily_volume.csv and gdelt_daily_tone.csv")


if __name__ == "__main__":
    main()
