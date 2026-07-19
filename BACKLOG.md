# Backlog: datacenter-media-sentiment

Resume-from-cold-session state, saved 2026-07-19. Repo is COMPLETE and committed
through the data phase (last commits: uniform promotional filter + comparison
classification). All datasets validated; the publication drafting phase has not started.

## Open

### Analyses
- [ ] Water-coverage deep dive — the KETOS-strategic cut, NOT YET DONE. Track the
      environment_water theme plus "water" keyword frequency in datacenter headlines
      over time (data: data/processed/census_classified.csv theme column +
      data/raw/bigquery_census.csv title/url text). Question: when did water become a
      mainstream datacenter issue, how fast is it growing vs energy, and where does it
      rank among mitigable backlash themes. Feeds whitepaper's "implications for
      developers" section and one blog post. Ganesh explicitly wants this angle.
- [ ] Local-vs-national diffusion lag (paper section 3) — bucket domains into local
      TV/newspaper vs trade vs national; test whether local negativity leads national
      by months. Data ready in census_classified.csv + comparison files.

### Publications (task list #9)
- [ ] arXiv paper draft — target physics.soc-ph (Ganesh has cond-mat arXiv standing;
      may need one endorsement; SSRN fallback). Neutral framing rule (see memory:
      feedback-neutral-framing). Spine: (1) two-frame GDELT method + LLM/tone
      calibration (r=0.93 datacenter, 0.69 crypto, ~0.5 5G/wind; flat-regime caveat
      for fracking), (2) datacenter flip (+54% 2022 -> -5% 2026, first net-negative
      March 2026), (3) six-technology comparison: figs 08/09, datacenter = largest/
      fastest sustained decline from first place; 5G/wind recovered in 3-4 months,
      recovery window framing, (4) robustness: promo filter (crypto 2025 spike was
      22% promotional content), crypto frame-drift-to-AI caveat, QC 98.8/87.2/92.8,
      zero pos<->neg flips. Constructive close for infrastructure developers.
- [ ] Whitepaper for KETOS site — paper content + explicit developer implications +
      water-stewardship positioning (uses the water deep-dive).
- [ ] Blog series (4-5 posts): the flip / the benchmark / local early-warning /
      water+energy themes / methods+open-data.
- [ ] LinkedIn arc — hook post exists at LINKEDIN_DRAFT.md (gitignored; needs GitHub
      link inserted); add benchmark post using charts 08/09; 10K-impression goal.

### Polish
- [ ] Chart 03: ChatGPT annotation collides with bars; footnote truncates on right.
- [ ] Chart 08: footnote note that datacenter line starts slightly below 0 (pre-boom
      baseline year already contained early decline).
- [ ] README: add comparison-study section (six-technology census, promo filter,
      calibration numbers); currently documents only the datacenter study.
- [ ] User actions: push repo to GitHub; insert repo URL into LINKEDIN_DRAFT.md.

## Done
- [x] Datacenter volume census (335k fulltext / 103k headline-frame), verified vs API
- [x] 8,100 datacenter headlines classified, QC'd (98.8/87.2/92.8, 0 pos<->neg flips)
- [x] Six-technology comparison census (920k articles, 2015-2026, BigQuery)
- [x] 9,187 comparison headlines classified (Sonnet fleets), quarterly series built
- [x] Uniform PR/promo filter after Ganesh caught spurious crypto 2025 spike; all
      findings held, datacenter finding strengthened; raw series kept as annex
- [x] Face-validity + commerce-content audits on all six topics (all clean)
- [x] Charts 01-09 final; gallery artifact:
      https://claude.ai/code/artifact/a584f78e-4f49-4e63-88d1-e87f130463dd
- [x] Repo git-initialized, ~10 commits, clean tree
