# Headline Classification Rubric

This exact rubric was given to the LLM classifier (Claude Sonnet) for every batch of
headlines. Each headline is classified independently, using only the headline text
and the source domain.

## Fields

For each headline, assign:

### 1. `relevant` (yes | no)

Is the article substantively about data centers - the facilities, their construction,
operation, economics, energy/water use, or their industry?

- `yes`: the data center (or datacenter industry/buildout) is a main subject.
- `no`: "data center" appears incidentally (e.g., a company profile that mentions the
  firm operates data centers, a market-research boilerplate listing, an unrelated
  product announcement, sports/entertainment listings, an article about a stock that
  happens to be a datacenter REIT without discussing facilities).

Market-research press releases ("Data Center Cooling Market worth $X billion by 20XX")
count as `relevant: yes` (they are about the datacenter industry) - classify their
sentiment per the rules below.

### 2. `sentiment` (positive | negative | neutral) - only meaningful when relevant=yes

The attitude toward data centers / datacenter development *as conveyed by the headline*.
Not the general mood of the article; specifically whether data centers are cast
favorably, unfavorably, or neutrally.

- `positive`: investment/expansion framed as growth or opportunity, job creation,
  economic development wins, innovation/efficiency achievements, community benefit,
  clean-energy deals, favorable approvals framed positively.
- `negative`: opposition/protests, moratoriums and rejections, environmental harm,
  water or electricity strain, rising utility bills blamed on data centers, noise,
  health concerns, outages/failures, lawsuits, fraud, security breaches, bubble/
  overbuild worries, job-loss or displacement framing.
- `neutral`: factual/technical/market reporting without valence (earnings, specs,
  routine deals, "X considers building Y"), balanced pro/con coverage, or headlines
  whose valence cannot be determined.

Judge the headline's framing, not your own view of data centers. A headline can be
negative about a company but neutral toward data centers; classify the attitude
toward data centers.

If relevant=no, set sentiment to `neutral` by convention (it is excluded from
sentiment aggregates anyway).

### 3. `theme` (one of 8) - the dominant topic

- `energy_grid`: electricity demand, grid strain, power deals, nuclear/renewables for
  datacenters, utility bills.
- `environment_water`: water use, emissions, pollution, land use, noise, wildlife.
- `community_opposition`: local protests, zoning fights, moratoriums, referendums,
  NIMBY disputes, community pushback or negotiations.
- `investment_buildout`: new construction, expansions, land purchases, capex
  announcements, financing, M&A, market growth reports.
- `jobs_economy`: employment, tax revenue, local economic impact.
- `policy_regulation`: legislation, government strategy, permitting reform, tariffs,
  national AI-infrastructure policy.
- `tech_operations`: cooling, chips/hardware, architecture, efficiency, security,
  outages, operations.
- `other`: anything else (including relevant=no rows).

## Output format

For each headline id, output exactly:
`{"id": <id>, "relevant": "yes|no", "sentiment": "positive|negative|neutral", "theme": "<theme>"}`
