# 2026-05-03 | Stage K | COMPLETE | 2011+ Incremental Refresh

## Summary

Stage K refreshed the metadata-only 2011+ corpus with the 9 tests missing from
the Stage D archive:

- `15517`, `15518`, `15519`, `15528`, `15531`, `15532`, `15534`, `15539`, `15540`

The Stage D archive was preserved. The refresh was built as new ignored runtime
artifacts under `data/`, with this report as the durable tracked closeout.

Metadata refresh status: complete.

Classification/accounting status: complete. The refresh DB classifier run covers
3900 rows, classifies all 9 new tests, and the tracked v1.4.2/v1.6 fixture
lineage has been promoted from 3891 rows to 3900 rows.

## Inputs

Stage D source artifacts:

- Manifest:
  `D:\vscode\nhtsa_metadata_runtime_archive\stage_d_2026-04-30\full_2011plus_authoritative_manifest.csv`
- SQLite DB:
  `D:\vscode\nhtsa_metadata_runtime_archive\stage_d_2026-04-30\full_2011plus_metadata_only_stage_d_2026-04-30.sqlite`
- Manifest SHA-256:
  `B4A1262938D33793BFF0D4ACA78222E4BAB51C7253D4084FBB80597096ABE6BE`
- DB SHA-256:
  `B715779E81DD050511742F6DD8DCF45AED884163738C89EA0E86AD41C8BF9F70`

New ignored runtime artifacts:

- `data/incremental_refresh_2026-05-03_missing_9_manifest.csv`
- `data/incremental_refresh_2026-05-03_missing_9_live_evidence.json`
- `data/full_2011plus_authoritative_manifest_refresh_2026-05-03.csv`
- `data/full_2011plus_metadata_only_refresh_2026-05-03.sqlite`

## Manifest Result

Refresh manifest acceptance checks:

| Check | Result |
| --- | ---: |
| Row count | 3900 |
| Duplicate `test_no` | 0 |
| Missing or parse-failed `test_date` | 0 |
| Pre-2011 rows | 0 |
| Date range | `2011-01-03` to `2025-11-19` |
| 2026-date rows | 0 |

The 9 appended rows are all in scope by `test_date >= 2011-01-01`; `model_year`
was recorded only as metadata and was not used for scope.

| test_no | test_date | configuration | type | vehicle |
| ---: | --- | --- | --- | --- |
| 15517 | 2025-10-01 | VEHICLE INTO POLE | OPTIONAL NEW CAR ASSESSMENT TEST | 2026 HYUNDAI IONIQ 9 |
| 15518 | 2025-09-30 | IMPACTOR INTO VEHICLE | OPTIONAL NEW CAR ASSESSMENT TEST | NHTSA DEFORMABLE IMPACTOR |
| 15519 | 2025-10-02 | VEHICLE INTO BARRIER | OPTIONAL NEW CAR ASSESSMENT TEST | 2026 HYUNDAI IONIQ 9 |
| 15528 | 2025-10-14 | VEHICLE INTO BARRIER | OPTIONAL NEW CAR ASSESSMENT TEST | 2026 HYUNDAI SANTA FE |
| 15531 | 2025-10-17 | VEHICLE INTO POLE | OPTIONAL NEW CAR ASSESSMENT TEST | 2026 TESLA MODEL Y |
| 15532 | 2025-10-16 | IMPACTOR INTO VEHICLE | OPTIONAL NEW CAR ASSESSMENT TEST | NHTSA DEFORMABLE IMPACTOR |
| 15534 | 2025-10-15 | VEHICLE INTO BARRIER | OPTIONAL NEW CAR ASSESSMENT TEST | 2026 TESLA MODEL Y |
| 15539 | 2025-11-18 | IMPACTOR INTO VEHICLE | OPTIONAL NEW CAR ASSESSMENT TEST | NHTSA DEFORMABLE IMPACTOR |
| 15540 | 2025-11-19 | VEHICLE INTO POLE | OPTIONAL NEW CAR ASSESSMENT TEST | 2026 CHEVROLET SILVERADO 1500 |

## Collection Result

Live access was bounded and explicit:

- `NHTSA_METADATA_ALLOW_LIVE=true`
- `--source live`
- `--allow-live`

Collection was restricted to the 9-row append manifest. No file downloads,
waveform analysis, UI work, full crawler work, or Stage D DB in-place overwrite
was performed.

Collect result:

- Collection run: `6`
- New payloads collected from the 9-row manifest: `150`
- Canonical rows inserted during collect: `2478`
- New tests present after collect: `9`

Endpoint backfill result:

- Backfill run: `7`
- Endpoint: `intrusion_info`
- Missing payloads fetched: `9`
- Failed requests: `0`
- Existing payloads skipped: `4048`
- No new `test_no` added during backfill: true

Rebuild note:

- A full 3900-test catalog rebuild was attempted but exceeded the 30-minute
  operational window and was stopped.
- The copied refresh DB passed `integrity_check` and `quick_check` afterward.
- Final canonical/read-model consistency was produced by targeted rebuild for
  the 9 new tests plus facet rebuild.

Refresh DB counts after collection and rebuild:

| Table | Rows |
| --- | ---: |
| `tests` | 3900 |
| `source_payloads` | 66477 |
| `source_payload_observations` | 66477 |
| `canonical_row_sources` | 1382222 |
| `instrumentation_channels` | 471566 |
| `media_assets` | 290845 |
| `code_values` | 757 |
| `test_filter_summary` | 3900 |
| `test_facets` | 1297 |

## Refresh Validation

Endpoint completeness against the refresh manifest:

- Manifest tests: `3900`
- Canonical DB tests: `3900`
- Manifest tests missing in DB: `0`
- DB tests not in manifest: `0`
- Missing endpoint matrix entries: `0`

Required endpoint payload counts:

| Endpoint | Payloads |
| --- | ---: |
| `test_summary` | 3900 |
| `metadata_export` | 3900 |
| `test_detail` | 3900 |
| `vehicle_info` | 3900 |
| `barrier_info` | 3900 |
| `occupant_info` | 3900 |
| `multimedia_files` | 3900 |
| `vehicle_documents` | 3900 |
| `intrusion_info` | 4057 |
| `restraint_info` | 5633 |
| `instrumentation_info` | 25587 |

Schema audit:

- Scope in-scope tests: `3900`
- Scope violations: `0`
- Read-model violations: `0`
- Canonical duplicate groups: `0`
- Canonical duplicate rows: `0`
- Asset classification counting invariant: `pass`
- Data-package candidate unclassified count: `0`
- Empty endpoints and unmapped fields remain audit diagnostics, not hard
  failures, under the current endpoint empty-success policy.

Code values:

- Rebuilt code sets: `17`
- Rebuilt code values: `757`
- Result remains consistent with Stage D total.

Schema contract validation:

- Result: `pass`
- Hard failures: `0`
- Warnings: `1`
- Warning: `source_payload_observations('source_payload_id')` is not an explicit
  critical index.

Endpoint matrix validation:

- Result: `pass`
- Endpoint contracts: `16`
- Hard failures: `0`
- Warnings: `0`

## Classification Impact

The refresh DB was classified directly from the SQLite snapshot using the
existing v1.4 rule file and no live API calls.

Direct refresh classifier result:

- Total rows: `3900`
- Classified rows: `3853`
- Unclassified rows: `47`
- Known false positives: `0`
- Classification rate: `0.987949`
- Live API used: `false`
- CLI exit code: `1`, because 47 rows remain unclassified in the classifier
  output.

All 9 newly appended tests were classified:

| test_no | status | canonical_rule_id |
| ---: | --- | --- |
| 15517 | classified | `US_NCAP_SIDE_POLE_20MPH_75DEG_25CM` |
| 15518 | classified | `US_NCAP_SIDE_BARRIER_MDB_38_5MPH_3015LB` |
| 15519 | classified | `US_NCAP_FRONTAL_FULL_WIDTH_RIGID_BARRIER_35MPH` |
| 15528 | classified | `US_NCAP_FRONTAL_FULL_WIDTH_RIGID_BARRIER_35MPH` |
| 15531 | classified | `US_NCAP_SIDE_POLE_20MPH_75DEG_25CM` |
| 15532 | classified | `US_NCAP_SIDE_BARRIER_MDB_38_5MPH_3015LB` |
| 15534 | classified | `US_NCAP_FRONTAL_FULL_WIDTH_RIGID_BARRIER_35MPH` |
| 15539 | classified | `US_NCAP_SIDE_BARRIER_MDB_38_5MPH_3015LB` |
| 15540 | classified | `US_NCAP_SIDE_POLE_20MPH_75DEG_25CM` |

Classification fixture promotion result:

- `total_count = 3900`
- `canonical_label_classified_count = 3881`
- `adjudicated_noncanonical_count = 19`
- `unadjudicated_count = 0`
- `accounted_for_count = 3900`
- `classification_evidence_v1_4_2.csv` data rows: `3900`
- `classification_lineage_audit_v1_6.csv` data rows: `3900`
- Stage K appended fixture rows: `9`
- Stage K lineage status: complete for all 9 new rows

## Default Verification

Default verification paths did not require live NHTSA access.

| Command | Result |
| --- | --- |
| `pytest -q` | pass, `131 passed`, 2 existing collection warnings |
| `ruff check scripts src tests` | pass |
| `mypy src\nhtsa_metadata` | pass |
| `powershell -ExecutionPolicy Bypass -File scripts\verify.ps1` | pass |
| `powershell -ExecutionPolicy Bypass -File .harness\run.ps1` | pass |

Targeted fixture promotion checks:

| Command | Result |
| --- | --- |
| `pytest -q tests/test_classifier_v1_4_2_targeted_expansion.py` | pass, `5 passed` |
| `pytest -q tests/test_classification_lineage_v1_6.py` | pass, `3 passed` |
| `pytest -q tests/test_classification_accounting.py` | pass, `3 passed` |

## Runtime Artifacts Not For Commit

The following runtime outputs are intentionally under ignored `data/` paths:

- refresh manifests and live evidence JSON
- refresh SQLite DB
- endpoint completeness JSON/stdout
- schema audit JSON/stdout
- code values rebuild JSON/stdout
- schema contract validation JSON/Markdown
- endpoint matrix validation JSON/Markdown
- refresh classifier JSON/Markdown/stdout

## Residual Risks

1. The final rebuild path used targeted rebuild after the full 3900-test rebuild
   exceeded the operational time window. Endpoint completeness, schema audit,
   contract validation, matrix validation, and default verification all passed
   on the resulting snapshot.
2. Future latestness audits should retain the direct `test_no` tail check. A
   broad by-search/year discovery path can miss newly published tail records if
   upstream pagination or search indexing lags.

## Closeout Status

Stage K metadata refresh and classification fixture promotion are complete. The
ignored runtime snapshot remains under `data/`, while tracked fixture lineage and
this report now represent the 3900-row 2011+ corpus.
