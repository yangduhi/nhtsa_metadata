# Schema v1.1 Full-Cover Decision

## Scope
- 2011+ metadata-only NHTSA crash/test catalog.
- No file download, no media URL fetch, no package parsing.
- Full-scale Stage D collect remains separate owner approval.

## Full Manifest Evidence
- row count: 3260
- date range: 2011-01-03 to 2021-12-02
- duplicate test_no: 0
- missing/parse-failed date: 0
- pre-2011 rows: 0
- anchors: 7201=True, 10001=True, 10003=True

## Schema Contract Validation
- result: pass
- hard failures: 0
- warnings: 1
- source_payload immutability, lineage, and prohibited index policy were validated.

## Endpoint Matrix Validation
- result: pass
- hard failures: 0
- warnings: 0
- instrumentation_detail_info decision: deferred_optional for v1.1 metadata-only full-scale collection.
- empty successful payload remains auditable and is not a failure.
- summary links are not endpoint authority.

## Representation Gap
- 1500 DB overlap with full manifest: 1170
- full manifest only tests: 2090
- 1500 DB only tests: 330
- overlap ratio of full: 0.3589
- key gap: live by-search full manifest stops at 2021, while the 1500 actual-crash DB includes 2022-2025.
- implication: before Stage D, choose whether live by-search alone is authoritative or whether a reference-seeded discovery supplement is required.

## Manual Domain Review Backlog
- total: 215
- high/medium/low risk: 0/215/0
- blocker count: 0
- actions: {'defer': 136, 'new_code_value_candidate': 78, 'new_column_candidate': 1}

## Capacity Estimate
- estimated full tests from live by-search manifest: 3260
- estimated source/detail payload requests: 55802
- estimated SQLite DB size bytes: 2185826140
- SQLite/PostgreSQL recommendation: sqlite_possible_for_full_scale_metadata_only
- caveat: this estimate follows the 3,260-row live by-search manifest; reference-supplemented discovery needs a recomputed estimate.

## Decision
- full-cover schema readiness: conditional
- full-scale collect readiness: conditional approval-pass only after owner resolves the discovery authority decision.
- full crawler executed: no.
- detail endpoint collect executed: no.
- file download executed: no.
- next recommended action: decide whether Stage D uses live by-search only or a documented reference-seeded discovery supplement, then rerun the manifest gate if needed.
