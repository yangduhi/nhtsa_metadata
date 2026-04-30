# DRAFT: Full-Scale 2011+ Crawler Prompt

This is a draft prompt only. Not execution approval.

## Current Decision

Stage D full-scale collect must not run unless the owner explicitly approves Stage D in the current thread.

Discovery authority has been resolved for the v1.2 full-cover gate:

- selected authority: `reference_seeded_live_validated`
- authoritative manifest: `data/full_2011plus_authoritative_manifest.csv`
- manifest meta: `data/full_2011plus_authoritative_manifest.meta.json`
- authoritative manifest rows: 3891
- source mix:
  - `live_by_search`: 3260
  - `live_year_slice_by_search`: 608
  - `reference_seed_live_validated`: 23
- date range: 2011-01-03 to 2025-09-25
- duplicate/pre-2011/missing-date hard gates: 0

## Goal

Run the approved full-scale 2011+ NHTSA crash test metadata collection only after owner approval and after the discovery authority gate passes.

## Required Pre-Conditions

- Branch starts from the latest `main`.
- Working tree has no staged data artifacts.
- `pytest`, `ruff`, `mypy`, `scripts/verify.ps1`, and `.harness/run.ps1` pass.
- Live safety negative checks pass.
- `discovery_authority_decision` is documented.
- `schema_v1_2_full_cover_gate` is pass.
- The authoritative manifest path is `data/full_2011plus_authoritative_manifest.csv`.
- Manifest hash is recorded.
- Manifest duplicate test_no = 0.
- Manifest pre-2011 rows = 0.
- Manifest missing/parse-failed date = 0.
- Schema contract hard failures = 0.
- Endpoint matrix hard failures = 0.
- Source payload immutability and lineage gates pass.
- Prohibited whole-column `payload_json`/`raw_row_json` indexes are absent.
- v1.4 classification smoke or post-run classifier gate is planned.
- Owner explicitly approves full-scale Stage D in the current thread.

## Discovery Authority Gate

The live by-search full manifest alone is not accepted as the full 2011+ universe because it returns only 2011-2021 rows while year-slice by-search returns official 2022-2025 rows.

The selected authority is `reference_seeded_live_validated`:

- First use `full by-search ∪ year-slice by-search` as the official live discovery base.
- Use the reference DB only as a seed for rows still missing from live discovery.
- Include reference-seeded rows only when official live validation confirms `test_no` and an in-scope parseable `test_date`.
- Use live values where validation provides them.

## Hard Boundaries

- Do not download files.
- Do not fetch media URLs.
- Do not parse waveform, TDMS, UDS, EV, ABF, ISO, or ZIP contents.
- Do not use `modelYear` as scope.
- Do not use `test_no` range as scope.
- Use `test_date >= 2011-01-01`.
- Do not commit `data/` artifacts.

## Staged Commands

Stage A: build manifest only with live safety gate.

Stage B-0: edge-case candidate manifest review only. No live collect, no endpoint detail fetch, no media/file/package parsing.

Stage B-1: approved bounded metadata-only validation. Limit <=100 selected tests, metadata endpoints only, source payload persisted, no file download, no media fetch, no package parsing.

Stage C: verify existing 1000/1500 DB parity without new collection.

Stage D: full 2011+ collect. This requires separate owner approval after discovery authority and manifest gates pass.

Stage E: post-run endpoint completeness, schema audit, code_values rebuild, v1.4 classification coverage report, and final scale report.

Stage E required checks:

- endpoint completeness
- schema audit
- schema optimization
- code_values rebuild
- capacity/scale report
- API smoke

## Stop Conditions

Stop immediately if any safety gate is bypassed, any file download begins, source payloads fail to persist, pre-2011 canonical rows appear, duplicate groups become non-zero, discovery authority is unresolved, semantic hard failures appear, or P0/P1 schema/source conflicts appear.
