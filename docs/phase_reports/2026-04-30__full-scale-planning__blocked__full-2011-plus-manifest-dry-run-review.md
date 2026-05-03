# 2026-04-30 | Full-scale planning | BLOCKED | Full 2011+ Manifest Dry Run Review

## Scope
- live by-search/listing manifest-only dry run.
- No detail endpoint collect, no source_payload DB insert, no file download.
- Scope is `test_date >= 2011-01-01`; `test_no` and `modelYear` are not scope boundaries.

## Hard Gate
- row count: 3260
- date range: 2011-01-03 to 2021-12-02
- duplicate test_no: 0
- missing/parse-failed date in output: 0
- pre-2011 rows: 0
- scope_status values: ['in_scope']
- anchors: 7201=True, 10001=True, 10003=True

## Discovery Authority Finding
- reference DB 2011+ rows: 3888
- live manifest rows: 3260
- reference-only rows: 628
- live-only rows vs reference: 0
- actual 1500 DB-only rows vs live: 330
- actual DB-only date range: 2020-05-08 to 2025-09-23
- actual DB-only 2022-2025 rows: 322

## Decision
- Stage D full-scale collect: blocked.
- live by-search alone is not accepted as the full 2011+ universe.
- recommended authority: reference-seeded discovery supplement.
- a supplemented manifest gate and capacity estimate must pass before Stage D approval.

## Statement
- Detail endpoint collect: not executed.
- Full crawler: not executed.
- File/media download: not executed.
