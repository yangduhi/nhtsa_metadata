# Authoritative Full-Scale Capacity Estimate 2011+

## New Authoritative Estimate
- baseline_db_tests: 1500
- estimated_endpoint_requests: 66604
- estimated_full_tests: 3891
- estimated_sqlite_db_size_bytes: 2609049018
- scale_factor: 2.594
- sqlite_recommendation: sqlite_possible_for_full_scale_metadata_only

## Comparison With v1.1 Live-Only Estimate
- estimated_full_tests: old=3260 new=3891
- estimated_endpoint_requests: old=55802 new=66604
- estimated_sqlite_db_size_bytes: old=2185826140 new=2609049018
- sqlite_recommendation: old=sqlite_possible_for_full_scale_metadata_only new=sqlite_possible_for_full_scale_metadata_only

## Runtime Estimates
- delay=0.1s: request delay 1.85 hours
- delay=0.2s: request delay 3.7 hours
- delay=0.5s: request delay 9.25 hours
- delay=1.0s: request delay 18.5 hours

## Operational Requirement
- Use resumable collection runs.
- Back up DB before Stage D.
- Keep `data/` artifacts ignored.
