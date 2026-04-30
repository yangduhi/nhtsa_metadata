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
