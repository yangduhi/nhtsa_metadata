# 2026-04-30 | Full-scale planning | SUPERSEDED | Full-Scale Schema Capacity Estimate

## Status
- This estimate is valid only for the current live by-search manifest.
- Stage D remains blocked until discovery authority is decided.
- If `reference_seeded_discovery_supplement` is selected, rebuild the supplemented manifest and recompute this estimate.

## Current Live By-Search Estimate
- estimated_full_tests: 3260
- baseline_db_tests: 1500
- scale_factor: 2.1733
- estimated_endpoint_requests: 55802
- estimated_sqlite_db_size_bytes: 2185826140
- sqlite_recommendation: sqlite_possible_for_full_scale_metadata_only

## Required Recompute Gate
```text
If discovery_authority != live_by_search_only:
    rebuild supplemented manifest
    rerun duplicate/date/pre-2011 gates
    recompute endpoint request estimate
    recompute SQLite size estimate
    rerun endpoint matrix coverage estimate
```

## Runtime By Delay For Current 3260-Row Manifest
- delay=0.1s: request delay 1.55 hours
- delay=0.25s: request delay 3.88 hours
- delay=0.5s: request delay 7.75 hours
- delay=1.0s: request delay 15.5 hours
