# Data Center Media Coverage and Sentiment (2022-2026)

An open dataset and analysis of how English-language news covers data centers: monthly article volume and headline sentiment from January 2022 through June 2026, spanning the period before and after ChatGPT's launch on November 30, 2022.

**Headline findings:**

- Monthly news volume about data centers grew **10.9x** (838 headline-level articles in January 2022 to 9,120 in June 2026; 103,341 total).
- The growth did not start with ChatGPT. Coverage was flat through 2023 and inflected in early 2024, then accelerated sharply from mid-2025.
- Sentiment collapsed as volume exploded. Net sentiment (share of positive minus negative headlines) ran **+54% in 2022** and **-5% in 2026**. March 2026 was the first month where negative coverage outweighed positive.
- The story changed subject: community opposition rose from **5% of coverage themes in 2022 to 22% in 2026**, and energy/grid strain from 6% to 15-20%.
- Two independent measures agree: GDELT's lexicon-based tone over all 103k articles fell from **+1.09 to -0.35** over the same span, with no LLM involved.

## What is in this repository?

- `data/processed/monthly_sentiment.csv`: monthly sentiment and theme shares from LLM-classified headline samples (the core dataset)
- `data/processed/monthly_headline_census.csv`: monthly article counts and mean GDELT tone over the headline-frame census
- `data/processed/monthly_volume.csv`: monthly counts of all articles mentioning data center terms anywhere in the text (broader frame), with GDELT-wide normalization
- `data/processed/census_classified.csv`: all 8,100 sampled headlines with their classifications
- `data/raw/`: the 103k-article census, daily volume and tone series, samples, and QC files
- `charts/`: publication-ready PNGs
- `scripts/` and `sql/`: the complete, re-runnable pipeline
- `classification/rubric.md`: the exact classification rubric given to the LLM

## Where does the data come from?

All news data comes from the [GDELT Project](https://www.gdeltproject.org/), which monitors global online news. Two frames are used:

1. **Headline frame (primary, for sentiment).** Every article whose URL slug contains a data center term (`data center`, `datacenter`, `data centre`, and variants), extracted from GDELT's Global Knowledge Graph via its free public BigQuery dataset (`sql/census_query.sql`). This is a complete census: 103,341 unique English-language articles across all 54 months. URL-slug mention is a strict filter that selects articles substantively about data centers; 94% of sampled headlines were confirmed relevant by classification.
2. **Fulltext-mention frame (secondary, for the broad volume series).** Daily counts of all articles mentioning those terms anywhere in the text, from the GDELT DOC 2.0 API (335,206 articles). The two frames' monthly volumes correlate at r = 0.93.

Scope: English-language sources worldwide, January 1, 2022 to June 30, 2026.

## How is sentiment measured?

Two independent measures that cross-validate each other:

1. **LLM-classified headline sentiment** (primary). For each month, 150 articles are drawn from the census with a seeded random sample. Each headline is classified by Claude Sonnet against the committed rubric (`classification/rubric.md`): relevance, sentiment toward data centers (positive, negative, neutral), and one of 8 themes. Sentiment shares are computed over relevant headlines only (median 141 per month).
2. **GDELT average tone** (secondary). A lexicon-based score computed by GDELT for every article in the census, aggregated monthly. Cruder (it measures overall document language, not attitude toward data centers), but it covers all 103k articles and is fully independent of the LLM.

### Headline recovery

GDELT's census provides URLs; headline text was recovered by fetching each sampled article's live page title (72% of the sample). Where pages are gone or blocked, the headline is reconstructed from the URL slug (28%; flagged in `title_source`). Slug-derived titles carry the headline's words without casing or punctuation. The slug share is highest in 2026 (80%) because modern bot protection blocks automated fetches more often on recent pages; classification treats both forms identically.

### Classification quality control

- A seeded random 10% of the census sample (400 headlines, plus an earlier 120-headline pass on a preliminary frame) was re-classified in independent second passes with shuffled ordering.
- Agreement: **relevance 98.8%, sentiment 87.2%, theme 92.8%**.
- The sentiment disagreements are structurally benign for the study's metric: **zero of 400 double-classified headlines flipped between positive and negative**. All disagreements were adjacent (neutral versus a valenced label), symmetric across passes, and net out to a **0.8 percentage point** difference in net sentiment, against yearly swings of 60 points.
- The main source of neutral-versus-positive variance is "market to reach $X billion" press releases, whose valence is genuinely ambiguous; the rubric treats them as relevant, and both passes agree on that.
- 20 additional classifications were hand-checked during assembly; all were defensible, with 2 debatable theme (not sentiment) calls.

## Key findings

### Volume

- Headline-frame articles per month: 838 (Jan 2022) to 9,120 (Jun 2026), a 10.9x increase, with the steepest growth in 2025 and 2026.
- As a share of all GDELT-monitored English news, data center coverage (fulltext frame) rose 7.2x, from 0.05% to 0.37%.
- Coverage also became more headline-level: 15% of articles mentioning data centers led with them in 2022, versus 48% in the first half of 2026, a shift from background mention to primary subject.

### Sentiment

Net sentiment of relevant headlines (positive share minus negative share):

| Year | Positive | Negative | Net |
|------|----------|----------|-----|
| 2022 | 66% | 12% | +54% |
| 2023 | 59% | 10% | +49% |
| 2024 | 61% | 13% | +48% |
| 2025 | 51% | 22% | +28% |
| 2026 (H1) | 31% | 37% | **-5%** |

- March 2026 is the first net-negative month in the series; by June 2026 net sentiment reached -15 points.
- GDELT's independent lexicon tone shows the same shape: +1.09 in January 2022, crossing zero in late 2025, -0.35 by June 2026.

### Themes

- Community opposition (protests, zoning fights, moratoriums): 5% of relevant coverage in 2022, 22% in 2026.
- Energy and grid strain: roughly 6% in 2022, peaking near 29% in some late-2024 and 2025 months as power became the industry's defining constraint in the press.
- Investment and buildout announcements remain the largest single theme throughout but fell from roughly half of coverage to about a third.

## Known limitations

- **Headline-only sentiment.** Classification sees the headline and source domain, not the article body. Headlines are a standard proxy in media analysis but reflect editors' framing choices.
- **Frame definition.** The census requires a data center term in the URL slug. Articles about the industry that never name it in the headline (for example, some AI-infrastructure policy stories) are excluded. The broad fulltext series is published alongside for comparison.
- **English only.** Non-English coverage is not represented.
- **GDELT coverage bias.** GDELT's source list is broad but over-represents online and wire content, including press-release distributors. The relevance filter and theme labels make this visible rather than hiding it: market-research press releases are a large, consistent share of positive-to-neutral coverage.
- **Slug-derived titles** (28% of the sample, 80% in 2026) lose casing and occasionally truncate. QC found no systematic sentiment effect, but individual labels on garbled slugs are lower-confidence; `title_source` flags every affected row.
- **GDELT outages.** GDELT has no data for 2023-03-23 and 2025-06-15 through 2025-07-01. Affected months are flagged in `monthly_volume.csv` and on charts.
- **LLM classification is imperfect.** The rubric, QC agreement rates, and every individual label are published so the classification can be audited or re-run (`scripts/classify_headlines.py` with an Anthropic API key).
- **Annex: preliminary fulltext-frame sample.** Before the census pipeline, 10 months (Jan-Oct 2022) were sampled from the fulltext frame via the GDELT DOC API (`data/processed/annex_artlist_classified.csv`). Yearly means agree with the census frame (+51% versus +54% net); month-level values in that annex are noisier (about 30 relevant headlines per month).

## How to reproduce

1. Run `sql/census_query.sql` in BigQuery (free sandbox tier suffices; GDELT's dataset is public). Export to `data/raw/bigquery_census.csv`.
2. `python3 scripts/fetch_timelines.py` for the fulltext-frame daily series (respects GDELT API rate limits).
3. `python3 scripts/census_sample.py` draws the seeded 150/month sample and recovers headlines.
4. `python3 scripts/classify_headlines.py` classifies with Claude Sonnet (needs `ANTHROPIC_API_KEY`); `--qc` runs the double-classification pass.
5. `python3 scripts/aggregate.py` and `python3 scripts/make_charts.py` build the monthly datasets and charts.

All randomness is seeded; seeds are committed in the scripts.

## License and attribution

- Code: MIT (see `LICENSE`)
- Data, findings, and charts: CC BY 4.0 with [KETOS (ketos.co)](https://ketos.co) as the designated attribution party; underlying news metadata derived from the [GDELT Project](https://www.gdeltproject.org/) and redistributed with attribution per GDELT's terms of use
- Classification: Claude Sonnet (Anthropic); rubric in `classification/rubric.md`

If you use this data or these findings, you must credit **KETOS ([ketos.co](https://ketos.co))** with a link, alongside the GDELT Project. Suggested citation: *KETOS (2026). Datacenter Media Sentiment: a two-frame GDELT study. https://ketos.co* - see `CITATION.cff`.
