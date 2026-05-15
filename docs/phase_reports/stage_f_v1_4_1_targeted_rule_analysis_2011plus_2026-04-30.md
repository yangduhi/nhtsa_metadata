# Stage F v1.4.1 Targeted Rule Analysis 2011+

## 1. v1.4 baseline summary
- total_count: 3891
- classified_count: 3844
- unclassified_count: 47
- known_false_positive_count: 26
- multi_candidate_count: 1643
- multi_rule_family_count: 1222
- alias_used_count: 606
- fallback_used_count: 852
- generic_used_count: 572
- aggregate_used_count: 195
- metadata_gap_used_count: 666

## 2. failure set extraction method
- v1.4 baseline was reproduced from the Stage D SQLite snapshot and v1.4 rule file.
- Failure sets were frozen from v1.4 JSON: 47 unclassified rows and 26 known false-positive rows.
- Manifest SHA256 verified: `b4a1262938d33793bff0d4aca78222e4bab51c7253d4084fbb80597096abe6be`.

## 3. 47 unclassified triage summary
- out_of_scope_for_current_taxonomy: 6
- requires_new_canonical_label: 28
- source_payload_anomaly: 2
- true_metadata_gap: 11
- Full row-level triage: `tests/fixtures/classification/classification_gap_triage_v1_4_1.csv`.

## 4. 26 false-positive triage summary
- side_pole_over_confirmed: 8
- sled_full_vehicle_false_positive: 18
- Full row-level triage: `tests/fixtures/classification/known_false_positive_triage_v1_4_1.csv`.

## 5. side pole over-confirmed root cause
- v1.4 allowed weak side-pole text and inferred pole barrier evidence to confirm NCAP side pole without core NCAP/New Car Assessment evidence.
- Eight RESEARCH / VEHICLE INTO POLE rows with FMVSS pole title text were routed to a research-specific side-pole rule.

## 6. sled/full vehicle crash confusion root cause
- v1.4 full-vehicle RMDB/OMDB rules outranked sled evidence when test_configuration was `SLED WITH VEHICLE BODY`.
- Eighteen sled-with-body records are now blocked from full-vehicle crash candidates and classified as frontal oblique sled research.

## 7. negative rule changes
- Added classifier negative gate: sled records cannot match full-vehicle crash physical modes.
- Added classifier negative gate: NCAP side pole requires core NCAP/New Car Assessment plus pole evidence.

## 8. positive targeted rule changes
- Added `NHTSA_RESEARCH_SIDE_POLE_FMVSS_POLE_IMPACT_32KPH` for research FMVSS pole-title rows.
- Expanded `OCCUPANT_PERFORMANCE_FRONTAL_OBLIQUE_SLED_RESEARCH` to cover RMDB/OMDB frontal sled-with-body metadata.

## 9. rule priority changes
- Negative disambiguation is evaluated before positive/generic matching.
- Sled specificity now outranks generic full-vehicle oblique positive evidence.
- Side pole NCAP confirmation requires program evidence; research pole rows no longer depend on a generic fallback.

## 10. evidence model
- `classification_evidence_v1_4_1.csv` contains one row per manifest test.
- Each row records classifier version, final label/status, rule id/family, positive/negative evidence JSON, source payload ids, endpoints, field paths, and adjudication status.

## 11. remaining metadata/taxonomy gaps
- The original 47 unclassified rows are intentionally not force-classified.
- Remaining gaps are adjudicated as true metadata gaps, source payload anomalies, out-of-scope taxonomy gaps, or required new canonical labels.

## 12. exact acceptance conclusion
- v1.4.1 known_false_positive_count: 0.
- side pole over-confirmed: 0.
- sled classified as full vehicle crash: 0.
- ACCEPTED: classifier v1.4.1 accepted
