---
name: nhtsa-metadata-verify
description: Verify the nhtsa_metadata repo before closing a phase or before any bounded live pilot. Use for scripts/verify.ps1, .harness/run.ps1, live safety negative checks, and git/data artifact cleanliness checks.
---

# nhtsa_metadata Verify

Run this before closing work or before asking for approval to expand a pilot.

1. Confirm branch and worktree scope with `git status --short`, `git branch --show-current`, and `git rev-parse --short HEAD`.
2. Run default checks only: `pytest -q`, `ruff check src tests`, `mypy src\nhtsa_metadata`, `scripts\verify.ps1`, and `.harness\run.ps1`.
3. Confirm default checks do not call live NHTSA APIs.
4. Run live safety negative checks by removing `NHTSA_METADATA_ALLOW_LIVE` and verifying live manifest commands fail without output.
5. Confirm `git status --short --ignored data` shows `data/` outputs as ignored, not staged.
6. Report pass/fail with exact counts and any warnings.
