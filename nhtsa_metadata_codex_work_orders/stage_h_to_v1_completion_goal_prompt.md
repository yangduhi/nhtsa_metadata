# Stage H to v1.0 Completion Goal Prompt

```text
/goal

Goal:
Advance NHTSA_metadata from the completed Stage G integration baseline to the documented v1.0 project completion target.

Execution mode:
- This session is intentionally running in YOLO / full-access mode.
- Full local command and filesystem access is allowed.
- Local commits are allowed.
- Push is not allowed.
- Merge to main is not allowed.
- Live NHTSA API calls are not allowed.
- Production data rewrite is not allowed.

Mandatory workspace constraint:
- Work only in:
  D:\vscode\nhtsa_metadata
- Do not create a new git worktree.
- Do not create a new repository folder.
- Do not create a sibling project directory.
- Do not run git worktree add.
- Do not clone this repository.
- If branch isolation is needed, use branches only inside the current repository directory.
- If the current working tree is dirty and cannot be safely committed, stop and report instead of creating a new worktree.

Starting point:
- Current directory:
  D:\vscode\nhtsa_metadata
- Expected starting branch:
  codex/stage-g-schema-classifier-integration
- Stage G is implementation-complete.
- Stage H can start.

Project completion definition:
Do not define completion as:

  classified_count = 3891

Correct completion definition:

  total_count = 3891
  accounted_for_count = 3891
  known_false_positive_count = 0
  unadjudicated_count = 0
  schema_contract_hard_failure = 0
  endpoint_matrix_hard_failure = 0
  source_payload_immutability = pass
  migration_conflict = 0
  every row has traceable canonical classification evidence OR traceable final noncanonical disposition evidence

Critical interpretation:
- v1.4.1 is accepted for false-positive hardening and row-level adjudication.
- v1.4.1 is not accepted as an all-row canonical classifier.
- schema v1.5 is an integration baseline with documented exceptions.
- schema v1.5 is not the final operating evidence/disposition schema.
- Stage H should separate classification_status and disposition_status.
- Stage I should target only requires_new_canonical_label = 28.
- Stage I must not force:
  - true_metadata_gap = 11
  - out_of_scope_for_current_taxonomy = 6
  - source_payload_anomaly = 2
  into canonical labels.
- Stage J should implement the evidence-lineage operating model.

Known metrics:
Current Stage G / pre-v1.4.2 framing:

  total_count = 3891
  canonical_label_classified_count = 3844
  adjudicated_noncanonical_count = 47
  unadjudicated_count = 0
  known_false_positive_count = 0
  accounted_for_count = 3891

Expected post-v1.4.2 targeted canonical expansion framing:

  total_count = 3891
  canonical_label_classified_count = 3872
  adjudicated_noncanonical_count = 19
  unadjudicated_count = 0
  known_false_positive_count = 0
  accounted_for_count = 3891

Preflight:
1. Run:
   - pwd
   - git status -sb
   - git branch --show-current
   - git log --oneline -8
   - git worktree list --porcelain
2. Confirm:
   - current directory is D:\vscode\nhtsa_metadata
   - active branch is codex/stage-g-schema-classifier-integration or a clean descendant branch created in this same directory
   - no extra worktree is registered
   - no new worktree is created
   - working tree is clean
3. Read:
   - AGENTS.md
   - docs/project_completion_definition.md
   - docs/phase_reports/stage_g_schema_classifier_integration_result.md
   - docs/phase_reports/stage_h_classification_disposition_schema_plan.md
   - docs/phase_reports/stage_i_targeted_canonical_expansion_plan.md
   - docs/phase_reports/stage_j_schema_v1_6_evidence_model_plan.md

Branch policy:
- You may create a local branch in the current directory only if the working tree is clean.
- Recommended branch:
  codex/stage-h-to-v1-completion
- Do not create a worktree for this branch.
- Do not push.
- Do not merge to main.

Stage H objective:
Implement classification/disposition schema separation.

Required Stage H work:
1. Define classification_status separately from disposition_status.
2. Add or update schema structures for:
   - test_classification
   - classification_adjudication
   - classification_evidence semantics
   - test_classification_candidates if needed
3. Add enums or equivalent constraints for:

classification_status:
- classified
- unclassified
- ambiguous
- generic_mode_only
- out_of_scope

disposition_status:
- canonical_label_assigned
- requires_new_canonical_label
- true_metadata_gap
- out_of_scope_for_current_taxonomy
- source_payload_anomaly
- manual_review_required
- adjudicated_no_action

4. Preserve 47-row triage:
   - requires_new_canonical_label = 28
   - true_metadata_gap = 11
   - out_of_scope_for_current_taxonomy = 6
   - source_payload_anomaly = 2
5. Add tests.
6. Add or update report:
   docs/phase_reports/stage_h_classification_disposition_schema_result.md
7. Validate.
8. Commit locally with:
   stage-h: implement classification disposition schema baseline

Stage H success criteria:
- classification_status and disposition_status are separate.
- accounted_for_count can be reported separately from canonical_label_classified_count.
- unadjudicated_count can be measured.
- 47-row triage can be represented.
- pytest -q passes.
- ruff check . passes.
- mypy src\nhtsa_metadata passes.

Stage I objective:
Implement v1.4.2 targeted canonical expansion for only the 28 requires_new_canonical_label rows.

Required Stage I work:
1. Add targeted canonical labels/rules only for the 28 requires_new_canonical_label rows.
2. Do not force true_metadata_gap rows into canonical labels.
3. Do not force out_of_scope_for_current_taxonomy rows into canonical labels.
4. Do not force source_payload_anomaly rows into canonical labels.
5. Preserve known_false_positive_count = 0.
6. Add false-positive regression tests.
7. Add fallback/generic regression checks.
8. Add or update report:
   docs/phase_reports/stage_i_v1_4_2_targeted_canonical_expansion_result.md
9. Validate.
10. Commit locally with:
    stage-i: add targeted canonical expansion v1.4.2

Stage I success criteria:
- canonical_label_classified_count expected target: 3872
- adjudicated_noncanonical_count expected target: 19
- unadjudicated_count = 0
- known_false_positive_count = 0
- accounted_for_count = 3891
- pytest -q passes.
- ruff check . passes.
- mypy src\nhtsa_metadata passes.

Stage J objective:
Implement schema v1.6 evidence-lineage operating model.

Required Stage J work:
1. Implement or define durable lineage from:
   source payload -> normalized feature -> candidate rule -> final classification or final disposition
2. Add or update tables or equivalent concepts:
   - test_classification
   - test_classification_candidates
   - classification_evidence
   - classification_adjudication
   - canonical_label_registry
   - rule_registry
   - program_standard_evidence
   - test_event_domain
   - impact_device_evidence
   - restraint_equipment_evidence
   - classification_feature_evidence
3. Add tests.
4. Add migration if needed.
5. Add or update report:
   docs/phase_reports/stage_j_schema_v1_6_evidence_model_result.md
6. Validate.
7. Commit locally with:
   stage-j: implement schema v1.6 evidence lineage model

Stage J success criteria:
- evidence lineage is traceable.
- canonical classification and noncanonical final disposition both have evidence surfaces.
- schema hard failures are zero or documented non-blocking.
- migration conflict = 0.
- pytest -q passes.
- ruff check . passes.
- mypy src\nhtsa_metadata passes.

Final v1.0 release-readiness objective:
Create final release-readiness report.

Required file:
docs/phase_reports/v1_0_release_readiness_report.md

The report must include:
1. completion gate table
2. evidence for each metric
3. validation commands and results
4. blocking issues
5. non-blocking documented exceptions
6. merge readiness decision
7. rollback plan
8. recommendation:
   - ready for main merge
   - not ready for main merge
   - ready with documented exceptions

Final validation:
Run:
- git status -sb
- pytest -q
- ruff check .
- mypy src\nhtsa_metadata

If appropriate and environment supports it:
- powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
- powershell -ExecutionPolicy Bypass -File .harness\run.ps1

Do not fabricate pass results.
If verify.ps1 or harness cannot run due to .venv environment assumptions, report that explicitly.

Final commit:
If v1.0 release-readiness report is complete and validation is acceptable, commit locally with:

  docs: add v1.0 release readiness report

Stop rules:
Stop if:
1. working tree becomes ambiguous
2. a validation blocker appears
3. a required artifact is missing
4. a migration conflict cannot be safely resolved
5. implementing the next stage would require live API calls
6. implementing the next stage would require forcing metadata gaps into canonical labels
7. a new worktree or new repo folder would be required

Final response format:
Return exactly these sections:

1. Branch used
2. Local commits created
3. Stage H result
4. Stage I result
5. Stage J result
6. v1.0 release-readiness result
7. Files changed
8. Validation commands run and results
9. Skipped validation and reason
10. Remaining blockers
11. Whether v1.0 completion target is reached
12. Whether main merge is recommended
13. Whether any hard constraint was violated
14. Recommended next command
```
