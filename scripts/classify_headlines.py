#!/usr/bin/env python3
"""Classify sampled headlines with Claude Sonnet 5 using the committed rubric.

Reads data/raw/headlines_sample.csv, classifies in batches of 40 against
classification/rubric.md, and writes data/processed/headlines_classified.csv
(id, month, seendate, title, domain, sourcecountry, relevant, sentiment, theme).

Checkpointed: already-classified ids are skipped on re-run.

QC mode (--qc): re-classifies a seeded random 10% of the sample in shuffled
order (independent batch composition) to data/processed/headlines_qc.csv,
then prints agreement rates against the main run.

Requires ANTHROPIC_API_KEY (or an `ant auth login` profile).
"""

import argparse
import csv
import json
import random
import sys
import time
from pathlib import Path

import anthropic

MODEL = "claude-sonnet-5"
BATCH_SIZE = 40
SEED = 20221130
ROOT = Path(__file__).resolve().parent.parent
RUBRIC = (ROOT / "classification" / "rubric.md").read_text()
THEMES = ["energy_grid", "environment_water", "community_opposition",
          "investment_buildout", "jobs_economy", "policy_regulation",
          "tech_operations", "other"]

SCHEMA = {
    "type": "object",
    "properties": {
        "classifications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "relevant": {"type": "string", "enum": ["yes", "no"]},
                    "sentiment": {"type": "string",
                                  "enum": ["positive", "negative", "neutral"]},
                    "theme": {"type": "string", "enum": THEMES},
                },
                "required": ["id", "relevant", "sentiment", "theme"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["classifications"],
    "additionalProperties": False,
}

SYSTEM = (
    "You classify news headlines about data centers for a media-sentiment study. "
    "Apply the following rubric exactly.\n\n" + RUBRIC
)


def classify_batch(client: anthropic.Anthropic, rows: list[dict]) -> dict[int, dict]:
    lines = [f'{r["id"]}\t[{r["domain"]}]\t{r["title"]}' for r in rows]
    prompt = (
        "Classify each headline below (format: id, source domain, headline). "
        "Return one classification per id.\n\n" + "\n".join(lines)
    )
    for attempt in range(5):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=8000,
                system=SYSTEM,
                output_config={"effort": "medium",
                               "format": {"type": "json_schema", "schema": SCHEMA}},
                messages=[{"role": "user", "content": prompt}],
            )
            text = next(b.text for b in response.content if b.type == "text")
            out = {c["id"]: c for c in json.loads(text)["classifications"]}
            missing = [r["id"] for r in rows if int(r["id"]) not in out]
            if missing:
                raise ValueError(f"missing ids in response: {missing}")
            return out
        except (anthropic.RateLimitError, anthropic.InternalServerError) as e:
            wait = 15 * (attempt + 1)
            print(f"  retry {attempt + 1} ({e.__class__.__name__}); waiting {wait}s",
                  file=sys.stderr)
            time.sleep(wait)
        except ValueError as e:
            print(f"  retry {attempt + 1} ({e})", file=sys.stderr)
    raise RuntimeError("batch failed after 5 attempts")


def run(sample_rows: list[dict], out_path: Path, label: str) -> None:
    done = set()
    if out_path.exists():
        with open(out_path) as f:
            done = {int(r["id"]) for r in csv.DictReader(f)}
        print(f"Resuming {label}: {len(done)} already classified")

    todo = [r for r in sample_rows if int(r["id"]) not in done]
    client = anthropic.Anthropic()
    write_header = not out_path.exists()
    with open(out_path, "a", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["id", "month", "gkg_date", "title", "domain",
                        "title_source", "relevant", "sentiment", "theme"])
        for i in range(0, len(todo), BATCH_SIZE):
            batch = todo[i:i + BATCH_SIZE]
            result = classify_batch(client, batch)
            for r in batch:
                c = result[int(r["id"])]
                w.writerow([r["id"], r["month"], r["gkg_date"], r["title"],
                            r["domain"], r["title_source"],
                            c["relevant"], c["sentiment"], c["theme"]])
            f.flush()
            print(f"{label}: {min(i + BATCH_SIZE, len(todo))}/{len(todo)}", flush=True)


def qc_agreement() -> None:
    main = {int(r["id"]): r for r in
            csv.DictReader(open(ROOT / "data/processed/headlines_classified.csv"))}
    qc = list(csv.DictReader(open(ROOT / "data/processed/headlines_qc.csv")))
    n = len(qc)
    agree = {"relevant": 0, "sentiment": 0, "theme": 0}
    for r in qc:
        m = main[int(r["id"])]
        for k in agree:
            agree[k] += r[k] == m[k]
    print(f"\nQC agreement over {n} double-classified headlines:")
    for k, v in agree.items():
        print(f"  {k}: {v}/{n} = {100 * v / n:.1f}%")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--qc", action="store_true",
                    help="re-classify a random 10%% and report agreement")
    args = ap.parse_args()

    with open(ROOT / "data/raw/census_sample.csv") as f:
        sample = list(csv.DictReader(f))

    if args.qc:
        rng = random.Random(SEED + 1)
        subset = rng.sample(sample, max(1, len(sample) // 10))
        rng.shuffle(subset)
        run(subset, ROOT / "data/processed/headlines_qc.csv", "qc")
        qc_agreement()
    else:
        run(sample, ROOT / "data/processed/headlines_classified.csv", "classify")


if __name__ == "__main__":
    main()
