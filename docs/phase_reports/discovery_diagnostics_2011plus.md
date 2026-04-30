# Discovery Diagnostics 2011+

## Scope
- Live by-search diagnostics only.
- No detail endpoint matrix collect, no file download, no package parsing.

## Summary
- full_by_search_row_count: 3260
- year_slice_union_count: 3724
- year_slice_manifest_row_count: 3724
- year_slice_missing_date_validation_count: 3
- year_slice_unresolved_missing_date_count: 0
- reference_2011plus_seed_count: 3888
- reference_only_count: 628
- live_only_count: 0
- year_slice_union_only_count: 608
- full_manifest_only_vs_year_slice_count: 144
- year_slice_duplicate_overlap_count: 0
- rows_2022_2025_present_in_year_slice: True

## Year Slices
- 2011: rows=400 unique=336 pages=4 termination=pagination_total_reached
- 2012: rows=500 unique=422 pages=5 termination=pagination_total_reached
- 2013: rows=500 unique=418 pages=5 termination=pagination_total_reached
- 2014: rows=400 unique=322 pages=4 termination=pagination_total_reached
- 2015: rows=300 unique=247 pages=3 termination=pagination_total_reached
- 2016: rows=490 unique=412 pages=5 termination=pagination_total_reached
- 2017: rows=362 unique=321 pages=4 termination=pagination_total_reached
- 2018: rows=229 unique=204 pages=3 termination=pagination_total_reached
- 2019: rows=200 unique=153 pages=2 termination=pagination_total_reached
- 2020: rows=269 unique=226 pages=3 termination=pagination_total_reached
- 2021: rows=200 unique=165 pages=2 termination=pagination_total_reached
- 2022: rows=148 unique=118 pages=2 termination=pagination_total_reached
- 2023: rows=200 unique=151 pages=2 termination=pagination_total_reached
- 2024: rows=200 unique=155 pages=2 termination=pagination_total_reached
- 2025: rows=100 unique=74 pages=1 termination=pagination_total_reached
- 2026: rows=0 unique=0 pages=1 termination=empty_page

## Diagnosis
- year-slice by-search returns additional official rows; authoritative manifest should use year-slice union or validated supplement
