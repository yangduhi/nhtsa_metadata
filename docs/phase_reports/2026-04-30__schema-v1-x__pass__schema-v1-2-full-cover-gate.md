# 2026-04-30 | Schema v1.x | PASS | Schema v1.2 Full-Cover Gate

## Retained Decisions
- Schema v1.0 raw/provenance/canonical/read-model decisions are retained.
- Schema v1.1 schema and endpoint contract validation are retained.
- Scope remains `test_date >= 2011-01-01`; modelYear/test_no are not scope boundaries.

## Discovery Authority
- selected authority: reference_seeded_live_validated
- authoritative manifest: data\full_2011plus_authoritative_manifest.csv
- manifest hash: b4a1262938d33793bff0d4aca78222e4bab51c7253d4084fbb80597096abe6be

## Gate Criteria
- authoritative manifest hard gates pass: True
- schema contract hard failures: 0
- endpoint matrix hard failures: 0
- source_payload immutability verified by schema contract.
- canonical lineage policy verified by schema contract.
- prohibited whole-column JSON indexes absent by schema contract.
- no file download boundary preserved.

## Decision
- schema v1.2 full-cover readiness: pass
- Stage D full-scale collect readiness: approval-ready
- Stage D requires separate owner approval in the current thread.
