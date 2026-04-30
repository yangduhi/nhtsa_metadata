# DRAFT: Full-Scale 2011+ Crawler Prompt

This is a draft prompt only. It is not execution approval.

## Goal

Run the approved full-scale 2011+ NHTSA crash test metadata collection after owner approval.

## Required Pre-Conditions

- Branch starts from the latest `main`.
- Working tree has no staged data artifacts.
- `pytest`, `ruff`, `mypy`, `scripts/verify.ps1`, and `.harness/run.ps1` pass.
- Live safety negative checks pass.
- Owner explicitly approves full-scale Stage D in the current thread.

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

Stage B: optional bounded validation if owner requests it.

Stage C: verify existing 1000/1500 DB parity without new collection.

Stage D: full 2011+ collect. This requires separate owner approval.

Stage E: post-run endpoint completeness, schema audit, schema optimization, code_values rebuild, scale report, and API smoke.

## Required Post-Run Reports

- full-scale manifest review
- endpoint completeness report
- schema audit report
- schema optimization report
- code_values rebuild report
- full-scale final report

## Stop Conditions

Stop immediately if any safety gate is bypassed, any file download begins, source payloads fail to persist, pre-2011 canonical rows appear, duplicate groups become non-zero, semantic hard failures appear, or P0/P1 schema/source conflicts appear.

## Schema v1.1 Full-Cover Update (2026-04-30)

This document is still a draft prompt only. It is not execution approval.
Stage D full collect must not run without separate explicit owner approval.

### v1.1 Manifest-Only Evidence

- live by-search full manifest path: `data/full_2011plus_manifest.csv`
- observed live by-search manifest rows: 3260
- observed date range: 2011-01-03 to 2021-12-02
- duplicate test_no: 0
- missing/parse-failed date: 0
- pre-2011 rows: 0
- anchors included: 7201=True, 10001=True, 10003=True

### v1.1 Contract Gates

- schema contract validator hard failures: 0
- endpoint matrix validator hard failures: 0
- instrumentation_detail_info: deferred_optional for metadata-only Stage D unless owner explicitly approves per-curve detail expansion.
- source payload immutability, lineage, and forbidden whole JSON index policies must remain passing.

### Discovery Authority Decision Required Before Stage D

The v1.1 dry run found a material discovery discrepancy: the live by-search manifest contains 2011-2021 rows, while the existing 1500 actual-crash DB includes 2022-2025 rows. Before Stage D, the owner must choose one discovery authority:

1. live by-search only, accepting the observed 3,260-row universe;
2. reference-seeded discovery supplement, with a new manifest gate and capacity estimate;
3. another official NHTSA discovery route, documented before collect.

### Capacity Estimate From Current Live Manifest

- estimated tests: 3260
- estimated endpoint requests: 55802
- estimated SQLite DB size: 2185826140 bytes
- runtime request-delay estimates: see `docs/phase_reports/full_scale_schema_capacity_estimate.md`

### Stage D Stop Conditions Addendum

Stop before detail collect if the manifest contains pre-2011 rows, missing/parse-failed dates, duplicate test_no, unresolved discovery authority discrepancy, schema contract hard failures, endpoint matrix contract hard failures, source_payload immutability failure, lineage failures, or prohibited `payload_json`/`raw_row_json` whole-column indexes.
