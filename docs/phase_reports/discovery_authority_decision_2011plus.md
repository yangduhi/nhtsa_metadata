# Discovery Authority Decision for 2011+ Full Manifest

## Conclusion
- selected authority: reference_seeded_live_validated
- Stage D readiness: approval-ready

## Evidence
- live by-search full count: 3260
- year-slice by-search union count: 3724
- full/year-slice official live union count: 3868
- year-slice-only rows added: 608
- year-slice-only rows without reference seed but test_summary validated: 3
- reference 2011+ seed count: 3888
- reference-only count: 23
- validated supplement count: 23
- excluded supplement count: 0
- final authoritative manifest count: 3891
- final date range: ['2011-01-03', '2025-09-25']
- duplicate test_no count: 0
- pre-2011 rows: 0
- missing/parse-failed rows: 0

## 2022-2025 Gap
- 2022-2025 rows present in year-slice by-search: True
- Full by-search alone stopped at 2021, but year-slice by-search returned official 2022-2025 rows.
- The authoritative live discovery base is therefore `full by-search ∪ year-slice by-search`, not full by-search alone.
- reference-only rows were validated against official live core endpoints.
- Live values take precedence where official validation provides values.

## Authority Rules
- Reference DB is seed only, not canonical source.
- Only validated live or validated live with metadata drift rows are included.
- Date conflict, out-of-scope, missing date, and manual-review rows are excluded.
- Manual review rows require separate owner approval before Stage D inclusion.

## Stage D Implication
- full-scale collect may use authoritative manifest: True
- owner approval is still required.
- file download/media fetch/package parsing remain prohibited.
