# 2026-05-03 | Stage G | COMPLETE | Schema Classifier Integration Result

## 1. Branch/worktree used

- Worktree: `D:\vscode\nhtsa_metadata_stage_g`
- Branch: `codex/stage-g-schema-classifier-integration`
- Starting point: `origin/codex/stage-d-full-scale-2011plus-collect`
- Foundation planning commit: `228e3ac docs: define project completion and stage roadmap`

## 2. Artifacts found

Schema v1.5 artifacts were found and integrated from
`origin/codex/stage-f-schema-contract-v15`:

- `docs/schema/schema_contract_v1_5.md`
- `docs/schema/endpoint_entity_matrix_v1_5.md`
- `docs/schema/field_catalog_v1_5.md`
- `docs/schema/code_value_contract_v1_5.md`
- `docs/schema/relationship_matrix_v1_5.md`
- `docs/phase_reports/stage_f_schema_contract_2011plus_2026-04-30.md`
- `data/schema/field_catalog_v1_5.csv`
- `data/schema/endpoint_entity_matrix_v1_5.csv`
- `data/schema/code_sets_v1_5.csv`
- `data/schema/code_values_v1_5.csv`
- `data/schema/relationship_matrix_v1_5.csv`
- `data/schema/schema_audit_v1_5.csv`
- `data/schema/stage_f_schema_artifact_registry_2011plus_2026-04-30.lock`
- `migrations/0003_schema_contract_v1_5.sql`
- `scripts/build_schema_contract_v1_5.py`
- `tests/test_schema_contract_v1_5.py`

Classifier v1.4.1 artifacts were found and integrated from
`origin/codex/stage-f-v141-targeted-rule-analysis`:

- `docs/phase_reports/stage_f_v1_4_1_targeted_rule_analysis_2011plus_2026-04-30.md`
- `docs/phase_reports/stage_f_classification_acceptance_2011plus_2026-04-30.md`
- `tests/fixtures/classification/classification_acceptance_v1_4_1.csv`
- `tests/fixtures/classification/classification_evidence_v1_4_1.csv`
- `tests/fixtures/classification/classification_gap_triage_v1_4_1.csv`
- `tests/fixtures/classification/classification_summary_v1_4_1.csv`
- `tests/fixtures/classification/known_false_positive_triage_v1_4_1.csv`
- `docs/us_fmvss_ncap_crash_test_classification_method_v1_4_1500sample_targeted_rules.json`
- `scripts/classifier_v1_4_1_acceptance.py`
- `src/nhtsa_metadata/services/rule_classifier.py`
- `tests/test_classifier_v1_4_1_acceptance.py`
- `tests/test_rule_classifier.py`

## 3. Artifacts missing

No required Stage F schema v1.5 or classifier v1.4.1 artifact was missing after
branch discovery and merge.

## 4. Files changed

Stage G adds or updates:

- Stage G/H/I/J planning documentation.
- Stage F schema v1.5 contract docs, derived schema CSV artifacts, migration SQL,
  generator script, artifact registry, and schema contract tests.
- Stage F classifier v1.4.1 rule hardening, acceptance tests, classifier reports,
  and regression fixture CSVs.
- `docs/phase_reports/stage_g_schema_classifier_integration_result.md`.

The classifier CSVs were moved from `data/classification/` to
`tests/fixtures/classification/` during Stage G to avoid treating generated
classifier acceptance artifacts as production data.

## 5. Branch merge result

- Schema v1.5 branch merge: `8ea9401 merge stage f schema contract v1.5 into stage g`
- Schema v1.5 Stage G reconciliation: `54f28c2 stage-g: reconcile schema v1.5 artifact baseline`
- Classifier v1.4.1 branch merge: `415b96f merge stage f classifier v1.4.1 into stage g`

Both Stage F branches were merged into the Stage G branch. No branch was merged
into `main`, and nothing was pushed.

## 6. Conflict resolution result

No Git merge conflicts occurred.

The schema branch did require Stage G compatibility cleanup after merge:

- The Stage F schema artifact registry had stale CSV hashes relative to the
  committed branch blobs. The CSV artifact contents were preserved and only the
  registry hashes were reconciled to the actual checked-in artifact bytes.
- `scripts/build_schema_contract_v1_5.py` needed minimal lint compatibility:
  a generated-report line-length/import-order file waiver and removal of one
  unused local variable.

## 7. Migration numbering result

Final migration order:

- `alembic/versions/0001_initial_schema.py`
- `alembic/versions/0002_discovery_provenance.py`
- `migrations/0003_schema_contract_v1_5.sql`

No migration number conflict was found. The schema v1.5 SQL migration remains
`0003_schema_contract_v1_5.sql`; no renumbering was required and migration
semantics were not changed.

## 8. classification_evidence reconciliation result

Stage G preserves separate meanings for evidence surfaces:

- DB table `classification_evidence`: schema v1.5 contract table for durable
  classification evidence linkage. It is an integration baseline surface, not
  the final Stage J evidence-lineage operating model.
- Classifier runtime evidence: rule/candidate evidence produced while evaluating
  rows in the classifier. It remains runtime behavior and is not a replacement
  for the DB table.
- `classification_evidence_v1_4_1.csv`: v1.4.1 regression fixture and audit
  artifact with one row per manifest test.
- Regression fixture: `tests/fixtures/classification/*.csv` files are used by
  `tests/test_classifier_v1_4_1_acceptance.py`.
- Audit artifact: Stage F classifier reports and CSVs document acceptance and
  adjudication evidence, but they are not raw source payloads or a final Stage J
  lineage schema.

No Stage J schema v1.6 evidence model was implemented in Stage G.

## 9. CSV artifact policy result

Final Stage G policy:

- Classifier v1.4.1 CSVs live under `tests/fixtures/classification/` because the
  current tests consume them as deterministic regression fixtures.
- Stage F classifier reports remain under `docs/phase_reports/`.
- Generated classifier acceptance CSVs must not be placed under production data
  paths by default.
- `scripts/classifier_v1_4_1_acceptance.py` now defaults `--output-dir` to
  `tests/fixtures/classification`.
- No raw source payload data was moved or modified.

## 10. Acceptance wording changes

Stage G uses this acceptance wording:

- v1.4.1 is accepted for false-positive hardening and row-level adjudication.
- v1.4.1 is not accepted as an all-row canonical classifier.
- schema v1.5 is accepted as an integration baseline with documented exceptions.
- schema v1.5 is not the final operating evidence/disposition schema.

Searches did not find misleading positive claims such as "all rows classified",
"v1.4.1 passed full corpus classification", or "schema v1.5 final operating
schema". Existing `classified_count = 3891` references are explicit anti-goals.

## 11. Acceptance metric framing

Current Stage G / pre-v1.4.2 framing:

- `total_count = 3891`
- `canonical_label_classified_count = 3844`
- `adjudicated_noncanonical_count = 47`
- `unadjudicated_count = 0`
- `known_false_positive_count = 0`
- `accounted_for_count = 3891`

Expected post-v1.4.2 targeted canonical expansion framing:

- `total_count = 3891`
- `canonical_label_classified_count = 3872`
- `adjudicated_noncanonical_count = 19`
- `unadjudicated_count = 0`
- `known_false_positive_count = 0`
- `accounted_for_count = 3891`

The original 47 triage remains:

- `requires_new_canonical_label = 28`
- `true_metadata_gap = 11`
- `out_of_scope_for_current_taxonomy = 6`
- `source_payload_anomaly = 2`

Stage G does not force true metadata gaps, taxonomy out-of-scope rows, or source
payload anomalies into canonical labels.

## 12. Validation commands and results

Validation run during Stage G:

- `pytest -q`: passed before Stage G merge, after schema merge cleanup, after
  classifier merge, after classifier CSV relocation, and after this result
  report was added.
- `ruff check .`: passed before Stage G merge, after schema merge cleanup, after
  classifier merge, after classifier CSV relocation, and after this result
  report was added.
- `mypy src\nhtsa_metadata`: passed before Stage G merge and after this result
  report was added.

Skipped validation:

- `powershell -ExecutionPolicy Bypass -File scripts\verify.ps1`: skipped because
  the script invokes `.venv\Scripts\python.exe` inside this Stage G worktree and
  no worktree-local `.venv` exists.
- `powershell -ExecutionPolicy Bypass -File .harness\run.ps1`: skipped because
  the harness delegates to `scripts\verify.ps1`, which requires the missing
  worktree-local `.venv`.

## 13. Remaining failures

No remaining test or lint failure is known at the time this report was written.

## 14. Stage G implementation completeness

Stage G is implementation-complete. Final validation passed and the final
Stage G integration commit was created locally.

## 15. Stage H readiness

Stage H can start from this integration baseline. Stage H should implement the
separated classification/disposition schema and adjudication model; it should
not reinterpret Stage G as all-row canonical classifier acceptance.

## 16. Hard constraint compliance

- No push performed.
- No merge to `main` performed.
- No live NHTSA API call performed.
- No raw source payload data modified.
- No production data rewrite performed.
- No Stage H schema overhaul implemented.
- No Stage I v1.4.2 canonical expansion implemented.
- No Stage J schema v1.6 evidence-lineage operating model implemented.
- No rows were forced into canonical labels.
