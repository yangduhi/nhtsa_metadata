# Stage F Schema Contract 2011+

## Conclusion
- schema_acceptance: ACCEPTED_WITH_DOCUMENTED_EXCEPTIONS: schema contract v1.5 is accepted with explicitly documented exceptions
- hard_failures: 0
- documented_exceptions: 455
- endpoint_hard_failures: 0
- classifier_logic_modified: false
- source_db_mutated: false
- main_merge_performed: false

## Worktree And Base
- worktree: `D:\vscode\nhtsa_metadata_stage_f_schema`
- branch: `codex/stage-f-schema-contract-v15`
- base_commit: `9f7612c10ff85a7e92d7ec54f2416eafa342b36c`
- base_branch: `codex/stage-d-full-scale-2011plus-collect`

## Source Baseline Verification
- manifest_rows: 3891
- collected_tests: 3891
- missing_tests: 0
- source_payloads: 66318
- payload_observations: 66318
- code_sets: 17
- code_values: 757
- manifest_sha256: `b4a1262938d33793bff0d4aca78222e4bab51c7253d4084fbb80597096abe6be`

## Produced Artifacts
- `docs/schema/schema_contract_v1_5.md`
- `docs/schema/endpoint_entity_matrix_v1_5.md`
- `docs/schema/field_catalog_v1_5.md`
- `docs/schema/code_value_contract_v1_5.md`
- `docs/schema/relationship_matrix_v1_5.md`
- `data/schema/field_catalog_v1_5.csv`
- `data/schema/endpoint_entity_matrix_v1_5.csv`
- `data/schema/code_sets_v1_5.csv`
- `data/schema/code_values_v1_5.csv`
- `data/schema/relationship_matrix_v1_5.csv`
- `data/schema/schema_audit_v1_5.csv`
- `data/schema/stage_f_schema_artifact_registry_2011plus_2026-04-30.lock`
- `migrations/0003_schema_contract_v1_5.sql`
- `tests/test_schema_contract_v1_5.py`
- `scripts/build_schema_contract_v1_5.py`

## Artifact Counts
- field_catalog_rows: 468
- endpoint_entity_matrix_rows: 21
- code_sets_rows: 17
- code_values_rows: 757
- relationship_matrix_rows: 26

## Audit Results
| audit_id | status | hard_failures | documented_exceptions | actual |
| --- | --- | --- | --- | --- |
| audit_1_source_baseline_verification | pass | 0 | 0 | manifest_rows=3891;collected_tests=3891;missing_tests=0;source_payloads=66318;observations=66318;code_sets=17;code_values=757;manifest_hash=b4a1262938d33793b... |
| audit_2_endpoint_to_entity_coverage | pass | 0 | 10 | endpoint_hard_failures=0;endpoint_rows=21 |
| audit_3_observed_json_path_coverage | pass | 0 | 420 | unknown_observed_field_count=0;field_catalog_rows=468 |
| audit_4_code_linkage | documented_exception | 0 | 25 | unlinked_code_field_hard_failures=0;linked_code_sets=17;documented_code_like_raw_fields=25 |
| audit_5_orphan_entity | pass | 0 | 0 | orphan_entity_count=0 |
| audit_6_provenance_completeness | pass | 0 | 0 | rows_missing_provenance=0 |
| audit_7_migration_sanity | pass | 0 | 0 | migration_sanity_status=pass |

## Verification Results
Final verification completed without live NHTSA API calls. The only residual notes are existing PytestCollectionWarning warnings for the SQLAlchemy TestFilterSummary model name.

- `pytest tests/test_schema_contract_v1_5.py: 3 passed`
- `pytest tests/test_schema_audit.py tests/test_schema_optimization.py tests/test_endpoint_completeness.py tests/test_full_cover_readiness.py tests/test_db_migrations.py: 20 passed`
- `ruff check src tests: passed`
- `mypy src\\nhtsa_metadata: passed`
- `pytest -q: 113 passed, 2 warnings`
- `scripts\\verify.ps1: passed, 113 pytest passed, 2 warnings`
- `.harness\\run.ps1: passed, 113 pytest passed, 2 warnings`

## DB Handling
- Source DB was opened as read-only input using SQLite URI `mode=ro`.
- The source DB was not copied for artifact generation.
- Migration sanity validation uses a temp DB only; the source DB is not migrated.
- No `.sqlite`, `.db`, media, raw payload archive, or large binary artifact is part of the schema contract artifact set.

## Classification Boundary
- v1.4 classification remains a known hard fail outside this thread: 47 unclassified and 26 known false positives.
- No classifier rule, classifier acceptance, false-positive repair, or unclassified repair was performed.
- `classification_evidence` is defined only as a schema/evidence surface.

## Final Decision
ACCEPTED_WITH_DOCUMENTED_EXCEPTIONS: schema contract v1.5 is accepted with explicitly documented exceptions
