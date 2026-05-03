# 2026-05-03 | Stage G | PLANNED | Schema Classifier Integration Plan

## 1. Purpose

Stage G integrates schema v1.5 and classifier v1.4.1 as an operating baseline without treating either as final v1.0 completion.

Stage G is the schema/classifier/disposition integration baseline. It is not final classifier completion.

## 2. Recommended branch

`codex/stage-g-schema-classifier-integration`

## 3. Starting point

Recommended starting point:

`origin/codex/stage-d-full-scale-2011plus-collect`

Before branching, confirm the remote branch exists and confirm which worktree owns Stage D artifacts. The expected `D:\vscode\nhtsa_metadata_stage_d` path was not present when this plan was authored.

## 4. Merge/reconcile order

1. Confirm clean or intentionally dirty worktree state.
2. Reconcile Stage D runtime/archive artifacts as read-only evidence, not production data to commit.
3. Bring in schema v1.5 contract documents and migrations only after checking current Alembic heads.
4. Bring in classifier v1.4.1 rule/report artifacts as evidence of false-positive hardening.
5. Reconcile classification/disposition metric semantics.
6. Regenerate reports from the selected DB or fixture only after the source and command are documented.
7. Run validation gates and record results in the Stage G report.

## 5. Schema v1.5 integration scope

Include:

- schema v1.5 contract acceptance with documented exceptions;
- migration numbering and head reconciliation;
- read-model compatibility checks;
- explicit distinction between schema acceptance and final evidence/disposition readiness.

Exclude:

- schema v1.6 evidence-lineage tables;
- production DB mutation;
- broad refactors unrelated to schema/classifier integration.

## 6. Classifier v1.4.1 integration scope

Include:

- false-positive hardening from v1.4 full-corpus failure package;
- reduction of `known_false_positive_count` to 0;
- preservation of row-level evidence for the original 47 unclassified rows;
- reporting that distinguishes canonical classification from final disposition.

Exclude:

- targeted canonical expansion for the 28 rows requiring new labels;
- forced classification of true metadata gaps, taxonomy out-of-scope rows, or source payload anomalies.

## 7. Migration numbering risk

Stage G must check:

- current Alembic head or heads;
- whether schema v1.5 introduces a conflicting revision id;
- whether any dirty local migration file exists;
- whether the intended starting branch already contains schema changes not reflected in current docs.

`migration_conflict = 0` is required before Stage G can be called done.

## 8. classification_evidence semantics reconciliation

Stage G must reconcile the current v1.4 evidence shape with future operating semantics:

- `matched_evidence_json` is not enough by itself because it only explains the winning match;
- `candidate_rules_json` and `candidate_rules_top5` must be preserved for auditability;
- false-positive cases require losing and winning candidate context;
- unclassified rows require evidence that candidate list was empty, not just that final rule is missing;
- final disposition evidence must be stored separately from classifier match evidence.

## 9. CSV artifact policy

CSV artifacts are review and handoff surfaces, not source of truth.

Required policy:

- source JSON or DB snapshot remains the evidence source;
- CSV files must include generation command, source path, row count, and hash when practical;
- CSV exports must not overwrite production data;
- failure manifests should remain bounded and reproducible;
- row-level CSV used for review must preserve `test_no`, source endpoint, source row path, source row hash, classifier status, and expected disposition fields.

## 10. Required metrics

Stage G must report:

- `total_count = 3891`
- `accounted_for_count = 3891`
- `canonical_label_classified_count = 3844` before v1.4.2
- `adjudicated_noncanonical_count = 47` before v1.4.2
- `known_false_positive_count = 0`
- `unadjudicated_count = 0`
- `schema_contract_hard_failure = 0`
- `endpoint_matrix_hard_failure = 0`
- `source_payload_immutability = pass`
- `migration_conflict = 0`

## 11. Validation commands

```powershell
git status
git diff --stat
git diff -- docs/project_completion_definition.md docs/phase_reports/
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1
pytest -q
ruff check .
mypy .
powershell -ExecutionPolicy Bypass -File .harness/run.ps1
```

If a command is unavailable or inappropriate, record the reason instead of reporting success.

## 12. Done criteria

Stage G is done when:

- the integration branch is based on the approved Stage D starting point;
- schema v1.5 is integrated as a baseline with documented exceptions;
- classifier v1.4.1 hardening is integrated with `known_false_positive_count = 0`;
- the 47 original unclassified rows are represented as final dispositions, not hidden failures;
- migration conflict count is zero;
- validation results are recorded;
- Stage H/I/J remain separate planned stages.

## 13. Non-goals

- Do not implement schema v1.6 evidence lineage.
- Do not implement v1.4.2 targeted canonical expansion.
- Do not force all 3891 rows into canonical labels.
- Do not modify production data.
- Do not run live NHTSA API calls.
- Do not merge, push, or commit without explicit approval.

## 14. Risks

- schema v1.5 migration numbering may conflict with current branch history;
- v1.4.1 artifacts may not be present in the current repo snapshot and may require artifact recovery;
- the distinction between false-positive hardening and all-row classifier acceptance can be lost in summary reporting;
- existing unrelated dirty changes can contaminate the integration diff.

## 15. Rollback points

- rollback to the pre-Stage G branch tip if migration heads conflict;
- rollback classifier artifact import if false-positive hardening reports are incomplete;
- rollback report regeneration if source DB or JSON provenance cannot be verified;
- rollback documentation changes if completion metric framing is rejected.
