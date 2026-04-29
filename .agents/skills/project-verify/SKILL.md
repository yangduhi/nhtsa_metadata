# Project Verify

Use this compatibility skill before closing a phase in `nhtsa_metadata`.

1. Prefer `.skills/nhtsa-metadata-verify/SKILL.md` for the full verification procedure.
2. Run `scripts/verify.ps1`.
3. Run `.harness/run.ps1`.
4. Confirm no live NHTSA call is required by default verification.
5. Confirm `data/` artifacts are ignored and not staged.
6. Record pass/fail results in `docs/phase_reports/`.
