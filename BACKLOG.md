# Backlog: datacenter-media-sentiment

Resume-from-cold-session state, saved 2026-07-19. Repo is COMPLETE and committed
through the data phase (last commits: uniform promotional filter + comparison
classification). All datasets validated; the publication drafting phase has not started.

## Open

### Publications (task list #9)
- [ ] arXiv submission — draft COMPLETE at paper/main.tex (compiled main.pdf, 10 pp,
      6 figs). Ganesh: review draft, then submit to physics.soc-ph (may need one
      endorsement; SSRN fallback). Corrected claims vs original spine: calibration
      r=0.92 quarterly datacenter (scripts/calibration.py, exact); 5G recovered in
      4 mo, wind 2 mo; datacenter = largest decline FROM NET-POSITIVE BASELINE
      (crypto raw drop larger from ~neutral); outlet section = levels not lag;
      circular-shift p<0.06 q / p<0.02 m. Note-added section covers post-window
      events (142 protests/42 states Jul 18; Reuters-Ipsos 14%/57% Jun 2026 poll;
      NY hyperscale moratorium Jul 14) — all web-verified.
- [ ] Whitepaper for KETOS site — paper content + explicit developer implications +
      water-stewardship positioning (uses the water deep-dive).
- [ ] Blog series (4-5 posts): the flip / the benchmark / local early-warning
      (reframe: levels not timing) / water+energy themes / methods+open-data.
- [ ] LinkedIn arc — hook post ready at LINKEDIN_DRAFT.md (GitHub link inserted);
      add benchmark post using charts 08/09; 10K-impression goal. BLOCKED on repo
      going public (Ganesh action, see below).

### Polish
- [ ] Chart 03: ChatGPT annotation collides with bars; footnote truncates on right.
- [ ] Chart 08: footnote note that datacenter line starts slightly below 0 (pre-boom
      baseline year already contained early decline).
- [ ] README: add comparison-study section (six-technology census, promo filter,
      calibration numbers); currently documents only the datacenter study.
- [ ] User action: flip https://github.com/ganesh-ketos/datacenter-media-sentiment
      from private to public (Settings > General > Danger Zone) before posting the
      LinkedIn hook or submitting to arXiv (paper's data-availability URL points
      there). Pushed private 2026-07-19 at Ganesh's direction.

## Done
- [x] Local-vs-national diffusion lag (2026-07-19) — scripts/classify_domains.py
      (API path) + Sonnet-fleet run (parts_domains/) -> domain_types.csv (1,979
      domains, 5 outlet types, rubric in classification/domain_rubric.md; QC 92.9%
      overall, 100% on local-vs-not); scripts/diffusion_lag.py -> diffusion_
      {monthly,quarterly}.csv + chart 12. FINDINGS (paper sec 3 must be reframed):
      NO lead-lag detected — local/national negative shares peak at lag 0 (r=0.74
      quarterly, r=0.68 monthly; each beats every circular-shift null realization,
      p<0.06 q / p<0.02 m at test resolution; symmetric decay), so "local leads national
      by months" is NOT supported at monthly resolution. The real finding is LEVELS:
      local runs ~13pp more negative throughout (mean 30.8% vs 18.0%; 2026-Q2 52.2%
      vs 31.5%) and is the ONLY outlet class to flip sustained net-negative
      (2025-Q3; national and trade never flip through 2026-Q2). Early-warning story
      for blog: watch local levels, not timing. Buckets n: local 1,980 / national
      1,434 / trade 2,387 relevant rows; wire_pr (1,716) excluded — fleet caught
      locality-named PR-syndication sites (malaysiasun.com etc.) via duplicate
      headlines.
- [x] Water-coverage deep dive (2026-07-19) — scripts/water_deep_dive.py; outputs
      data/processed/water_deep_dive_{monthly,quarterly}.csv, charts 10 (water vs
      energy) + 11 (backlash theme ranking). Headline findings for whitepaper/blog:
      water keyword mentions grew 2.4x (1.4% -> 3.2% of census, 2022-23 vs 2025-H1'26),
      slightly faster than energy keywords (2.1x) but from ~5x smaller base; water
      THEME share flat (~5-6%, single-label crowding by energy_grid which grew 2.5x
      to 16.8%); water = #3 negative-coverage theme both periods (behind community
      opposition, energy); water theme crossed 5% sustained in 2022-Q3, never 10%. Slug-keyword proxy validated vs fetched titles: recall 0.95,
      precision 0.83 (most "misses" are title-fetch failures, true precision higher).
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
