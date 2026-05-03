# 2026-04-30 | 1000-test expansion | ACCEPTED | 1000-Test 2011+ Schema Backlog Report

## Scope
- Based on the existing 1000-test 2011+ DB after bounded intrusion backfill.
- No schema migration was applied.
- No full crawler or file download was executed.

## Field Mapping Reconciliation
- Mapped fields before/after: 10 / 36
- Unmapped fields before/after: 287 / 274
- Extra JSON fields: 1
- Field profiles: 311
- Main change: source field alias reconciliation now recognizes canonical mappings for instrumentation, occupant, restraint, vehicle, and barrier detail endpoints.

## Recommendation Classifier Hardening
- Dictionary candidates before/after: 137 / 81
- Identifier no-action fields: 19
- Numeric measurement column candidates: 7
- Code values candidates: 1
- Column candidates: 1
- Index candidates: 17
- P0/P1/P2/P3: 0/0/241/19

## Dictionary Report Decision
- Selected option: report-only derived dictionary candidates.
- `code_values` DB population was not applied in this step to avoid migration/data mutation risk.
- Candidate domain outputs are included in `data/schema_optimization_report_2011plus_1000_hardened.json` under `dictionary_domain_report`.

## Source Conflict Taxonomy
- Total conflicts: 2233
- P0/P1/P2/P3: 0/0/0/2233
- By class: {'benign_alias_difference': 706, 'numeric_rounding_difference': 1527}
- Interpretation: observed conflicts are benign alias/format/rounding differences, not scope or semantic identity conflicts.

## Data Package Counting Invariant
- Candidate assets: 4960
- Classified assets: 4963
- Candidate unclassified count: 0
- Classified non-candidate assets: 3
- Status: pass
- Definition: classified assets can exceed vehicle-document candidates when multimedia/data-package URLs are classified from other source rows. The invariant is that candidate unclassified count must be zero.

## Test Facets And Read Model Coverage
- Facet rows after rebuild: 1050
- Present required facets: 26 / 27
- Missing required facets: ['dummy_type']
- Accepted note: `dummy_type` is absent in the current 1000-test payload coverage, so no facet row can be produced without fabricating a value.

## Test Classification Hardening
- unknown before/after: 105 / 0
- Newly classified count: 105
- Current distribution:
- pedestrian:classified: 99
- low_risk_deployment:classified: 90
- rollover:classified: 90
- sled_with_body:classified: 90
- frontal_barrier:classified: 89
- sled_without_body:classified: 89
- static_airbag:classified: 89
- side:classified: 87
- side_impactor:classified: 85
- frontal:classified: 79
- adas_fcw:classified: 45
- adas_ldw:classified: 31
- research_other:classified: 29
- rear:classified: 8

## Backlog
- P0: none.
- P1: none.
- P2: review dictionary/index candidates before a full-scale execution decision.
- Accepted warning: `dummy_type` facet remains data-absent in this pilot.
