-- Census of English-language news articles whose URL path mentions data centers,
-- Jan 2022 - Jun 2026, with GDELT's per-article tone score.
-- Source: GDELT Global Knowledge Graph (free public dataset on BigQuery).
-- Runs inside BigQuery's no-cost sandbox tier (~300 GB scanned, under the 1 TB/month free quota).
-- Output feeds data/raw/bigquery_census.csv.
SELECT
  DATE AS gkg_date,                                   -- yyyymmddhhmmss
  DocumentIdentifier AS url,
  CAST(SPLIT(V2Tone, ',')[OFFSET(0)] AS FLOAT64) AS tone
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE _PARTITIONTIME >= TIMESTAMP('2022-01-01')
  AND _PARTITIONTIME <  TIMESTAMP('2026-07-01')
  -- match the URL path only (not the domain, so trade outlets like
  -- datacenterdynamics.com do not match on every article)
  AND REGEXP_CONTAINS(
        REGEXP_REPLACE(LOWER(DocumentIdentifier), r'^https?://[^/]+', ''),
        r'data[-_]?cent(er|re)')
  -- English-language sources only (untranslated records)
  AND (TranslationInfo IS NULL OR TranslationInfo = '')
