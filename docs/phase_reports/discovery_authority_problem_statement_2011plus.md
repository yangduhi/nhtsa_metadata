# Discovery Authority Problem Statement 2011+

## Facts
- live by-search full manifest: 3260 rows, 2011-01-03 ~ 2021-12-02
- reference DB 2011+ parseable rows: 3888
- reference-only rows against full by-search: 628
- live-only rows against full by-search: 0
- existing 1500 actual-crash DB contains 2022-2025 rows

## Why Live By-Search Only Cannot Be Final Authority
- Full by-search returned no 2022-2025 rows, but year-slice by-search returned official 2022-2025 rows.
- The full by-search route alone therefore under-describes the 2011+ universe.
- Stage D cannot use a manifest that is known to omit official later-year rows.

## Why Reference DB Cannot Be Canonical
- `D:/vscode/pulse_analysis/data/db/nhtsa_data.db` is a bounded manifest seed reference.
- Its rows can identify candidate `test_no` values, but reference presence alone is not source authority.
- Reference-only rows must be validated by official live endpoints before inclusion.

## Required Resolution
- Use official live by-search full results plus year-slice by-search union as live discovery authority.
- Use reference DB only to seed rows not found by live discovery.
- Include reference-seeded rows only after official live validation confirms `test_no` and an in-scope parseable `test_date`.

## Conclusion
Schema v1.1 itself passed contract checks, but full-scale Stage D remains blocked until discovery authority is selected and documented. This v1.2 work resolves the authority path without approving Stage D execution.
