# 2026-04-30 | Edge-case validation | APPROVAL_REQUIRED | Edge-Case Schema Validation Candidate Plan

## Scope
- Candidate manifest only; no live collect approval is implied.
- Candidate rows are selected from full manifest rows not present in the 1500 DB.
- Limit: <= 100 test rows. This revision uses 90 test rows plus a separate field-level manual-domain sidecar.
- Stage B-0 is manifest review only. Stage B-1 bounded metadata validation requires separate owner approval.

## Summary
- candidate test rows: 90
- candidate file: `data\edge_case_schema_validation_candidate_manifest.csv`
- manual-domain sidecar: `data\edge_case_schema_validation_domain_review_candidates.json`
- full manifest only tests: 2090
- db only tests: 330

## Stratified Buckets
| bucket | target | selected | available | purpose |
| --- | --- | --- | --- | --- |
| SLED_WITH_VEHICLE_BODY | 15 | 15 | 66 | SLED WITH VEHICLE BODY drift and endpoint shape |
| SLED_WITHOUT_BODY_CHILD_RESTRAINT | 10 | 10 | 379 | FMVSS 213/213a/213b and research child-restraint sled drift |
| NCAP_CORE_ALIAS | 15 | 15 | 949 | NCAP frontal/side MDB/side pole alias and canonical collapse |
| FMVSS_COMPLIANCE_EDGE | 15 | 15 | 258 | FMVSS 208/214/301 compliance and v1.4 targeted-rule false-positive guard |
| RESEARCH_OBLIQUE_RMDB_VTV | 10 | 10 | 165 | research oblique/RMDB/VTV and generic-oblique reduction |
| STATIC_OOP_AIRBAG_LRD | 10 | 10 | 146 | static/OOP airbag and low-risk deployment separation from crash modes |
| PEDESTRIAN_CALIBRATION_COMPONENT | 10 | 10 | 105 | pedestrian aggregate contamination and calibration/component separation |
| PART581_NON_FMVSS_MISC | 5 | 5 | 22 | Part 581/non-FMVSS federal/miscellaneous schema domain check |

## Manual Domain Review Sidecar
- backlog total: 215
- risk high/medium/low: 0/215/0
- action counts: {"defer": 136, "new_code_value_candidate": 78, "new_column_candidate": 1}
- selected new_code_value_candidate: 8
- selected new_column_candidate: 1
- note: only one `new_column_candidate` exists in the current backlog; no synthetic second item was created.

## Decision
- Edge-case bounded validation remains optional and requires separate approval.
- This plan does not approve Stage D or any detail collect.
