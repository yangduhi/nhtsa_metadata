# Stage F Integration Acceptance 2011+

## 1. Integration Inputs
- schema branch: `origin/codex/stage-f-schema-contract-v15`
- schema commit: `6a74b5d7c25887b607f8d0e24f8149002e0869a1`
- classifier branch: `origin/codex/stage-f-v141-targeted-rule-analysis`
- classifier commit: `d4bab61d00fcedcfca4beadd8fcf03571258e17a`
- base branch: `origin/codex/stage-d-full-scale-2011plus-collect`
- base commit: `9f7612c10ff85a7e92d7ec54f2416eafa342b36c`
- schema merge commit: `7ab3ec812f7def3f14642f8db85159da550ba06d`
- classifier merge commit: `9428c1c77bd83f2bdcc2c11b316d0e9ca14a2f87`
- integration adjustment commit: `d80703c660c3eaf4dede6637979ea31b2eb0264e`
- final integration commit: `98ee326dcd3c5fc9057feab8409a49ff74f33787`
- hardening branch: `codex/stage-f-integration-hardening`
- source DB path: `D:\vscode\nhtsa_metadata_stage_d\data\full_2011plus_metadata_only_stage_d_2026-04-30.sqlite`
- manifest path: `D:\vscode\nhtsa_metadata_stage_d\data\full_2011plus_authoritative_manifest.csv`
- manifest SHA256: `b4a1262938d33793bff0d4aca78222e4bab51c7253d4084fbb80597096abe6be`

## 2. Git And Worktree Hygiene
- integration worktree path: `D:\vscode\nhtsa_metadata_stage_f_integration`
- hardening worktree path: `D:\vscode\nhtsa_metadata_stage_f_hardening`
- branch: `codex/stage-f-integration`
- main merge performed: false
- source DB handling: read-only source input; source DB was not migrated or copied.
- manifest handling: read-only source input; manifest was not modified.
- large artifact policy: no .sqlite, .db, media, raw payload archive, package download, or large binary artifact is part of the integration or hardening commit.
- compatibility hygiene wording: no .sqlite, .db, media, raw payload archive, or package download is committed.
- ignored data artifacts intentionally committed with -f: `data/schema/*.csv`, `data/schema/*.lock`, `data/classification/*.csv`, and `data/stage_f_integration_artifact_registry_2011plus_2026-04-30.lock`.

## 3. Schema Result Summary
- F-Schema conclusion: `ACCEPTED_WITH_DOCUMENTED_EXCEPTIONS: schema contract v1.5 is accepted with explicitly documented exceptions`
- schema hard failures: 0
- documented exceptions: 455
- endpoint exceptions: 10
- observed JSON path/documented field exceptions: 420
- code-like raw field documented exceptions: 25
- migration sanity result: pass
- source baseline: manifest rows 3891, collected tests 3891, missing tests 0, source payloads 66318, payload observations 66318, code sets 17, code values 757.
- schema test result: `pytest tests/test_schema_contract_v1_5.py -q` passed with 3 tests.

## 4. Classifier Result Summary
- F-Classifier conclusion: `ACCEPTED: classifier v1.4.1 accepted`
- original 47 adjudication breakdown:
  - `requires_new_canonical_label`: 28
  - `true_metadata_gap`: 11
  - `out_of_scope_for_current_taxonomy`: 6
  - `source_payload_anomaly`: 2
- original 26 false-positive repair result:
  - `side_pole_over_confirmed`: 8 repaired/adjudicated
  - `sled_full_vehicle_false_positive`: 18 repaired/adjudicated
- side pole over-confirmed final count: 0
- sled/full vehicle crash final count: 0
- known false-positive hard cases: 0
- fallback count: 852 -> 845
- generic count: 572 -> 565
- multi-candidate warning: +6; non-hard quality warning and Stage G improvement target.
- multi-rule-family warning: +4; non-hard quality warning and Stage G improvement target.
- classifier acceptance test result: `pytest tests/test_classifier_v1_4_1_acceptance.py -q` passed with 5 tests.

## 5. Reconciliation Result
- `data/schema/` and `data/classification/` coexist without path conflicts.
- `docs/phase_reports/` preserves both schema and classifier branch reports.
- artifact registries remain separated: schema registry under `data/schema/`; integration registry under `data/`; classifier artifacts under `data/classification/`.
- migration numbering status: no conflict. Integration contains only `migrations/0003_schema_contract_v1_5.sql`; classifier branch did not introduce a migration.
- conflict resolution performed: no Git file conflict occurred during either merge. Integration reconciliation updated schema registry byte/hash values previously and now documents classifier evidence mapping against schema contract surface.

## 6. Classification Evidence Mapping
The schema contract table `classification_evidence` is a normalized evidence surface. The classifier artifact `classification_evidence_v1_4_1.csv` is a row-per-test acceptance artifact. The following documented mapping reconciles the artifact columns to the contract surface without widening classifier logic.

| CSV column | Contract mapping | Integration requirement |
| --- | --- | --- |
| `canonical_test_uid` | `classification_evidence.canonical_test_uid` | Required for every row. |
| `classifier_version` | `classification_rules.rule_version` / provenance metadata | Required for every row. |
| `final_label` | `classification_evidence.classification_label` | Required when `final_status=classified`; blank is allowed for adjudicated unclassified rows. |
| `final_status` | `classification_evidence.evidence_status` | Required for every row; adjudicated statuses are explicit statuses, not silent failures. |
| `confidence` | `classification_evidence.provenance_json.confidence` | Required for every row. |
| `rule_id` | `classification_evidence.classification_rule_id` | Required for classified rows; documented adjudication marker for unclassified rows. |
| `rule_family` | `classification_rules.semantic_concept_id` / provenance metadata | Required for classified rows; adjudication category for unclassified rows. |
| `positive_evidence_json` | `classification_evidence.evidence_value` / `provenance_json.positive_evidence` | Required for every positive classification. |
| `negative_evidence_json` | `classification_evidence.provenance_json.negative_evidence` | Required where a negative gate or repair was applied; `{}` is allowed otherwise. |
| `source_payload_ids` | `classification_evidence.source_payload_id` repeated set | Required where source-backed evidence or adjudication exists. |
| `source_endpoints` | `classification_evidence.endpoint_name` repeated set | Required where source-backed evidence or adjudication exists. |
| `source_field_paths` | `classification_evidence.json_path` repeated set | Required where source-backed evidence or adjudication exists. |
| `adjudication_status` | `classification_evidence.provenance_json.adjudication_status` | `not_required`, `adjudicated`, or `accepted_repaired`. |
| `adjudication_note` | `classification_evidence.provenance_json.adjudication_note` | Required for adjudicated unclassified and accepted repaired rows. |

Evidence coverage result:
- classification evidence rows: 3891
- positive classification without source evidence: 0
- final classification without evidence: 0
- adjudicated unclassified rows without `adjudication_status`: 0
- adjudicated unclassified rows without `adjudication_note`: 0
- accepted adjudicated statuses: `true_metadata_gap`, `out_of_scope_for_current_taxonomy`, `requires_new_canonical_label`, `source_payload_anomaly`

## 7. Exit Semantics Resolution
- v1.4 baseline hard fail behavior is preserved: v1.4 remains a hard fail when the original 47 unclassified rows and 26 known false-positive rows are present.
- authoritative v1.4.1 acceptance signal returns exit 0 through `scripts/classifier_v1_4_1_acceptance.py` only when all hard acceptance rows pass.
- `tests/test_classifier_v1_4_1_acceptance.py` and `tests/test_stage_f_integration_acceptance.py` verify that adjudicated unclassified rows are not hard failures in v1.4.1 acceptance mode.
- legacy full-corpus CLI exit 1 is non-authoritative for Stage F v1.4.1 acceptance because it still treats intentionally adjudicated unclassified rows as unresolved generic classification failures.
- Because the legacy CLI exit 1 remains documented, the integration conclusion is `ACCEPTED_WITH_DOCUMENTED_EXCEPTIONS` rather than plain `ACCEPTED`.

## 8. Tests Executed
| command | result | notes |
| --- | --- | --- |
| `pytest tests/test_schema_contract_v1_5.py -q` | passed, 3 tests | No live API. |
| `pytest tests/test_classifier_v1_4_1_acceptance.py -q` | passed, 5 tests | No live API. |
| `pytest tests/test_stage_f_integration_acceptance.py -q` | passed, 5 tests | No live API. |
| `pytest -q` | passed, 125 tests, 2 warnings | Existing `TestFilterSummary` PytestCollectionWarning warnings only. |
| `ruff check src tests scripts` | passed | Hardening patch fixed `scripts/build_schema_contract_v1_5.py` lint-only issues without regenerating schema outputs. |
| `ruff check src tests scripts\classifier_v1_4_1_acceptance.py` | passed | Covers integration test files, runtime source, and the modified classifier acceptance script. |
| `ruff check src tests` | passed | Equivalent to the repo-local verify static check. |
| `mypy src\nhtsa_metadata` | passed | 48 source files, no issues. |
| `scripts\verify.ps1` | passed | Hardening patch allows `NHTSA_METADATA_VERIFY_PYTHON` when repo-local `.venv` is absent; executed with the Stage D virtualenv. |
| `.harness\run.ps1` | passed | Harness delegates to `scripts\verify.ps1`; executed with the same explicit verification Python. |
| `git diff --check` | passed | No whitespace errors. |

## 9. Final Conclusion
ACCEPTED_WITH_DOCUMENTED_EXCEPTIONS: Stage F integration accepted with explicitly documented exceptions
