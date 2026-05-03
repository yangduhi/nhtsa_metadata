# 2026-05-03 | Stage H to v1.0 | READY | Continuous Goal Readiness

## Purpose

Prepare the canonical `D:\vscode\nhtsa_metadata` checkout to run the Stage H to
v1.0 `/goal` workflow continuously through Stage H, Stage I, Stage J, and the
v1.0 release-readiness report.

## Canonical workspace

- Repository path: `D:\vscode\nhtsa_metadata`
- Active branch at preparation time: `codex/stage-g-schema-classifier-integration`
- Registered worktrees: only `D:/vscode/nhtsa_metadata`
- New worktree created: no
- New repository directory created: no
- Push performed: no
- Merge to `main` performed: no

## Prompt update

Updated:

- `nhtsa_metadata_codex_work_orders/stage_h_to_v1_completion_goal_prompt.md`

The prompt now explicitly requires continuous stage progression without user
approval gates between Stage H, Stage I, Stage J, and v1.0 release-readiness.
Each stage boundary is an internal validation and commit gate.

## Required context files present

- `AGENTS.md`
- `docs/project_completion_definition.md`
- `docs/phase_reports/stage_g_schema_classifier_integration_result.md`
- `docs/phase_reports/stage_h_classification_disposition_schema_plan.md`
- `docs/phase_reports/stage_i_targeted_canonical_expansion_plan.md`
- `docs/phase_reports/stage_j_schema_v1_6_evidence_model_plan.md`
- `nhtsa_metadata_codex_work_orders/stage_h_to_v1_completion_goal_prompt.md`

## Completion framing preserved

The prepared prompt preserves the project completion definition:

- Do not define completion as `classified_count = 3891`.
- Use `accounted_for_count = 3891`.
- Preserve `known_false_positive_count = 0`.
- Preserve `unadjudicated_count = 0`.
- Require traceable canonical classification evidence or traceable final
  noncanonical disposition evidence for every row.
- Keep `true_metadata_gap`, `out_of_scope_for_current_taxonomy`, and
  `source_payload_anomaly` as noncanonical final disposition categories.

## Baseline validation

Baseline validation ran before changing the prompt:

- `pytest -q`: passed, `120 passed, 2 warnings`.
- `ruff check .`: passed.
- `mypy src\nhtsa_metadata`: passed, `48 source files`.
- `powershell -ExecutionPolicy Bypass -File scripts\verify.ps1`: passed.
- `powershell -ExecutionPolicy Bypass -File .harness\run.ps1`: passed.

Post-update validation ran after updating the prompt and adding this readiness
report:

- `pytest -q`: passed, `120 passed, 2 warnings`.
- `ruff check .`: passed.
- `mypy src\nhtsa_metadata`: passed, `48 source files`.
- `powershell -ExecutionPolicy Bypass -File scripts\verify.ps1`: passed.
- `powershell -ExecutionPolicy Bypass -File .harness\run.ps1`: passed.

## Readiness result

Ready to run the prepared `/goal` prompt from:

- `D:\vscode\nhtsa_metadata`

Recommended launch:

```powershell
cd D:\vscode\nhtsa_metadata
codex --yolo
```

Then paste the content of:

```powershell
nhtsa_metadata_codex_work_orders\stage_h_to_v1_completion_goal_prompt.md
```

## Remaining risks

- Stage H/I/J are implementation stages and may reveal migration, test, or
  artifact blockers not visible during this readiness pass.
- Stage I must not absorb metadata gaps, taxonomy out-of-scope rows, or source
  payload anomalies into canonical labels.
- No push or main merge is authorized by the prepared prompt.
