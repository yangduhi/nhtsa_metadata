# Stage F Integration 2011+

## Conclusion
- integration_acceptance: ACCEPTED_WITH_DOCUMENTED_EXCEPTIONS: Stage F integration accepted with documented exceptions
- schema_branch: `origin/codex/stage-f-schema-contract-v15`
- schema_commit: `6a74b5d7c25887b607f8d0e24f8149002e0869a1`
- classifier_branch: `origin/codex/stage-f-v141-targeted-rule-analysis`
- classifier_commit: `d4bab61d00fcedcfca4beadd8fcf03571258e17a`
- base_branch: `origin/codex/stage-d-full-scale-2011plus-collect`
- base_commit: `9f7612c10ff85a7e92d7ec54f2416eafa342b36c`
- integration_branch: `codex/stage-f-integration`
- worktree: `D:\vscode\nhtsa_metadata_stage_f_integration`

## Merge Result
- `origin/codex/stage-f-schema-contract-v15`: merged with `--no-ff`, no file conflicts.
- `origin/codex/stage-f-v141-targeted-rule-analysis`: merged with `--no-ff`, no file conflicts.
- `docs/phase_reports/`: both branch reports preserved.
- `data/schema/` and `data/classification/`: separated and preserved.
- `tests/`: schema and classifier acceptance tests both preserved.
- migration numbering: no duplicate migration introduced by classifier branch; schema branch keeps `migrations/0003_schema_contract_v1_5.sql`.

## Integration Adjustment
- Updated `data/schema/stage_f_schema_artifact_registry_2011plus_2026-04-30.lock` for the six schema CSV artifact SHA-256 values observed in the integration worktree.
- No schema CSV contents, classifier outputs, source DB, raw payloads, or live access gates were changed by the integration adjustment.

## Conflict Checkpoints
- `classification_evidence` remains separated as classifier evidence output in `data/classification/classification_evidence_v1_4_1.csv`; schema contract surfaces remain under `data/schema/` and `docs/schema/`.
- Long-term DB-level reconciliation for `classification_evidence` is not performed in this integration branch.
- Artifact registries remain separated: schema registry under `data/schema/`; classifier artifacts under `data/classification/`.

## Verification Results
- `pytest tests/test_schema_contract_v1_5.py`: 3 passed.
- `pytest tests/test_classifier_v1_4_1_acceptance.py`: 5 passed.
- Verification used the existing Stage D virtualenv and did not call live NHTSA APIs.

## Documented Exceptions
- Schema branch carries its accepted documented exceptions from schema contract v1.5.
- Classifier branch carries non-blocking warning deltas for multi-candidate and multi-rule-family counts.
- Integration branch adds only the registry-lock hash reconciliation described above.
