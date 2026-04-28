# Operations

## Default Verification

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
```

This command runs linting, type checking, and tests. It must not call live NHTSA APIs.

## Harness

```powershell
powershell -ExecutionPolicy Bypass -File .harness\run.ps1
```

The harness delegates to `scripts/verify.ps1` in Phase 0.

## Live API Policy

Live API access is disabled by default. Phase 7 will introduce a manual validation command that
requires explicit live opt-in. Default tests and verification scripts must remain fixture/mock only.
