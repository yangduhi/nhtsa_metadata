# Project Ops Hardening Report

## Scope

- Add repo-local `.codex` and `.skills` guidance for 2011+ bounded metadata pilots.
- Harden `.agent`, `.harness`, `.env.example`, README, and contract docs before 100-test expansion.
- Do not change parser, canonical, schema, or live collection runtime logic.
- Do not run 100-test live collect, full crawler, file downloads, or waveform/data-package parsing.

## Completed

- Added `.codex/project.toml` with scope, verification, live policy, bounded pilot, and forbidden operation rules.
- Added repo-local skills for verification, live pilot, and scope audit workflows.
- Updated `.agents/skills` wrappers to point to the new `.skills` procedures.
- Expanded `.agent/project.json` with 2011+ scope, reference DB seed path, pilot defaults, and forbidden operations.
- Added harness preflight checks for required contract docs, `.env.example` 2011+ settings, and ignored `data/` pilot outputs.
- Added 2011+ and reference DB settings to `.env.example`.
- Rewrote corrupted Korean scope text in AGENTS and core contract/operations docs as UTF-8.
- Updated README to describe the project as a 2011+ NHTSA crash test metadata-only DB.
- Documented the 100-test expansion gate as manifest-only until separately approved.

## Verification

- pytest: passed (`84 passed`, 2 existing collection warnings).
- ruff: passed for `src` and `tests`.
- mypy: passed for `src\nhtsa_metadata`.
- scripts/verify.ps1: passed (`84 passed`, 2 existing collection warnings).
- .harness/run.ps1: passed with contract/env/data ignore preflight.
- skill validation: passed for all three `.skills/nhtsa-metadata-*` skills.
- config validation: `.codex/project.toml` and `.agent/project.json` parsed successfully.
- live safety negative: passed; both missing `--allow-live` and missing env var cases failed
  without creating `data/should_not_exist.csv`.
- data artifact ignored check: passed through harness `git check-ignore` preflight.

## Live Policy

- Default verification remains fixture/mock only.
- 100-test live collect remains out of scope until separately approved.
- Full crawler and file downloads remain forbidden.
