#!/usr/bin/env python3
"""Classify news domains by outlet type with Claude Sonnet 5.

Builds the unique-domain list from data/processed/census_classified.csv
(domains normalized by stripping port suffixes, with up to 3 sample headlines
each for context), classifies in batches of 40 against
classification/domain_rubric.md, and writes data/processed/domain_types.csv
(domain, n_rows, outlet_type).

Checkpointed: already-classified domains are skipped on re-run.

QC mode (--qc): re-classifies a seeded random 10% in shuffled order to
data/processed/domain_types_qc.csv, then prints agreement against the main run.

Requires ANTHROPIC_API_KEY (or an `ant auth login` profile).
"""

import argparse
import csv
import json
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import anthropic

MODEL = "claude-sonnet-5"
BATCH_SIZE = 40
SEED = 20221130
ROOT = Path(__file__).resolve().parent.parent
RUBRIC = (ROOT / "classification" / "domain_rubric.md").read_text()
TYPES = ["local", "national", "trade", "wire_pr", "other"]

SCHEMA = {
    "type": "object",
    "properties": {
        "classifications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string"},
                    "outlet_type": {"type": "string", "enum": TYPES},
                },
                "required": ["domain", "outlet_type"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["classifications"],
    "additionalProperties": False,
}

SYSTEM = (
    "You classify news website domains by outlet type for a media study. "
    "Apply the following rubric exactly.\n\n" + RUBRIC
)


def build_domain_list() -> list[dict]:
    counts = Counter()
    titles = defaultdict(list)
    with open(ROOT / "data/processed/census_classified.csv") as f:
        for r in csv.DictReader(f):
            d = r["domain"].split(":")[0]
            counts[d] += 1
            live = r["title_source"] == "live"
            titles[d].append((0 if live else 1, r["title"]))
    out = []
    for d, n in counts.most_common():
        samples = [t for _, t in sorted(titles[d])[:3]]
        out.append({"domain": d, "n_rows": n, "samples": samples})
    return out


def classify_batch(client: anthropic.Anthropic, rows: list[dict]) -> dict[str, str]:
    lines = []
    for r in rows:
        samples = " | ".join(t[:90] for t in r["samples"])
        lines.append(f'{r["domain"]}\t({r["n_rows"]} articles)\t{samples}')
    prompt = (
        "Classify each domain below (format: domain, article count in our sample, "
        "up to 3 sample headlines it published). Return one classification per "
        "domain, echoing the domain exactly.\n\n" + "\n".join(lines)
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
            out = {c["domain"]: c["outlet_type"]
                   for c in json.loads(text)["classifications"]}
            missing = [r["domain"] for r in rows if r["domain"] not in out]
            if missing:
                raise ValueError(f"missing domains in response: {missing}")
            return out
        except (anthropic.RateLimitError, anthropic.InternalServerError) as e:
            wait = 15 * (attempt + 1)
            print(f"  retry {attempt + 1} ({e.__class__.__name__}); waiting {wait}s",
                  file=sys.stderr)
            time.sleep(wait)
        except ValueError as e:
            print(f"  retry {attempt + 1} ({e})", file=sys.stderr)
    raise RuntimeError("batch failed after 5 attempts")


def run(domains: list[dict], out_path: Path, label: str) -> None:
    done = set()
    if out_path.exists():
        with open(out_path) as f:
            done = {r["domain"] for r in csv.DictReader(f)}
        print(f"Resuming {label}: {len(done)} already classified")

    todo = [d for d in domains if d["domain"] not in done]
    client = anthropic.Anthropic()
    write_header = not out_path.exists()
    with open(out_path, "a", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["domain", "n_rows", "outlet_type"])
        for i in range(0, len(todo), BATCH_SIZE):
            batch = todo[i:i + BATCH_SIZE]
            result = classify_batch(client, batch)
            for d in batch:
                w.writerow([d["domain"], d["n_rows"], result[d["domain"]]])
            f.flush()
            print(f"{label}: {min(i + BATCH_SIZE, len(todo))}/{len(todo)}", flush=True)


def qc_agreement() -> None:
    main = {r["domain"]: r["outlet_type"] for r in
            csv.DictReader(open(ROOT / "data/processed/domain_types.csv"))}
    qc = list(csv.DictReader(open(ROOT / "data/processed/domain_types_qc.csv")))
    agree = sum(r["outlet_type"] == main[r["domain"]] for r in qc)
    print(f"\nQC agreement over {len(qc)} double-classified domains: "
          f"{agree}/{len(qc)} = {100 * agree / len(qc):.1f}%")
    diff = Counter((main[r["domain"]], r["outlet_type"]) for r in qc
                   if r["outlet_type"] != main[r["domain"]])
    for (a, b), n in diff.most_common():
        print(f"  main={a} qc={b}: {n}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--qc", action="store_true",
                    help="re-classify a random 10%% and report agreement")
    args = ap.parse_args()

    domains = build_domain_list()
    print(f"{len(domains)} unique domains")
    if args.qc:
        rng = random.Random(SEED + 1)
        subset = rng.sample(domains, max(1, len(domains) // 10))
        rng.shuffle(subset)
        run(subset, ROOT / "data/processed/domain_types_qc.csv", "qc")
        qc_agreement()
    else:
        run(domains, ROOT / "data/processed/domain_types.csv", "classify")


if __name__ == "__main__":
    main()
