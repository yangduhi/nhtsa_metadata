# Stage F Classification Acceptance 2011+

## 1. v1.4 vs v1.4.1 metric comparison table

| metric | v1.4 | v1.4.1 | delta | status |
|---|---:|---:|---:|---|
| total_count | 3891 | 3891 | 0 | pass |
| classified_count | 3844 | 3844 | 0 | pass |
| unclassified_count | 47 | 47 | 0 | pass |
| known_false_positive_count | 26 | 0 | -26 | pass |
| multi_candidate_count | 1643 | 1649 | 6 | warn |
| multi_rule_family_count | 1222 | 1226 | 4 | warn |
| alias_used_count | 606 | 606 | 0 | pass |
| fallback_used_count | 852 | 845 | -7 | pass |
| generic_used_count | 572 | 565 | -7 | pass |
| aggregate_used_count | 195 | 195 | 0 | pass |
| metadata_gap_used_count | 666 | 659 | -7 | pass |
| manifest_rows | 3891 | 3891 | 0 | pass |
| manifest_sha256 | b4a1262938d33793bff0d4aca78222e4bab51c7253d4084fbb80597096abe6be | b4a1262938d33793bff0d4aca78222e4bab51c7253d4084fbb80597096abe6be |  | pass |

## 2. total/classified/unclassified/adjudicated counts
- total: 3891
- classified: 3844
- unclassified: 47
- original 47 unclassified adjudicated: 47

## 3. known false-positive count
- 0

## 4. side pole over-confirmed count
- 0

## 5. sled/full vehicle crash false-positive count
- 0

## 6. fallback/generic/alias/aggregate/metadata_gap counts
- fallback_used: 845
- generic_used: 565
- alias_used: 606
- aggregate_used: 195
- metadata_gap_used: 659

## 7. multi-candidate/multi-rule-family counts
- multi_candidate: 1649
- multi_rule_family: 1226

## 8. evidence coverage count
- classification_evidence rows: 3891
- final classification without evidence: 0
- positive classification without source evidence: 0

## 9. tests executed
- v1.4 baseline full corpus classification: reproduced expected failure and wrote baseline JSON/Markdown.
- v1.4.1 full corpus classification: completed with known false-positive hard cases at 0; CLI exit remained non-zero because 47 rows are still intentionally unclassified for adjudication.
- acceptance report generator: generated all Stage F CSV and Markdown artifacts.
- `pytest tests/test_classifier_v1_4_1_acceptance.py -q`: 5 passed.
- `pytest tests/test_rule_classifier.py -q`: 4 passed.
- `pytest -q`: 117 passed, 2 warnings.
- `ruff check src tests scripts/classifier_v1_4_1_acceptance.py`: passed.
- `mypy src\nhtsa_metadata`: passed.
- `scripts\verify.ps1`: not run because this throwaway worktree has no local `.venv`; equivalent default ruff/mypy/pytest checks were run with the existing Stage D virtualenv.

## 10. hard acceptance result

| check | expected | actual | status |
|---|---|---|---|
| total manifest rows | 3891 | 3891 | pass |
| manifest sha256 | b4a1262938d33793bff0d4aca78222e4bab51c7253d4084fbb80597096abe6be | b4a1262938d33793bff0d4aca78222e4bab51c7253d4084fbb80597096abe6be | pass |
| missing tests | 0 | 0 | pass |
| classification live API used | 0 | 0 | pass |
| package/media/file download | 0 | 0 | pass |
| known false-positive hard cases | 0 | 0 | pass |
| side pole over-confirmed | 0 | 0 | pass |
| sled classified as full vehicle crash | 0 | 0 | pass |
| original 47 unclassified all adjudicated | 47 | 47 | pass |
| classification evidence rows | 3891 | 3891 | pass |
| classification without evidence rows | 0 | 0 | pass |
| source evidence missing positive classifications | 0 | 0 | pass |
| negative evidence ignored known false-positive | 0 | 0 | pass |
| fallback_used not increased | <= 852 | 845 | pass |
| generic_used not increased | <= 572 | 565 | pass |
| no source DB mutation | verified | read-only sqlite connection | pass |
| tests/results recorded | present | present | pass |

- ACCEPTED: classifier v1.4.1 accepted
