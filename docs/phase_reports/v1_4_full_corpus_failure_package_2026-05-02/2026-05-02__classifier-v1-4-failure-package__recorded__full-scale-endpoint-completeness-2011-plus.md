# 2026-05-02 | Classifier v1.4 Failure Package | RECORDED | Full-Scale Endpoint Completeness 2011+

## Conclusion
- expected_tests: 3891
- collected_tests: 3891
- missing_tests: 0
- missing_endpoint_matrix_count: 0
- source_payload_count: 66318
- source_payload_observations_count: 66318
- lineage_rows: 1378515

## Endpoint Coverage

| endpoint | expected | actual | missing | empty_success | non_empty |
|---|---:|---:|---:|---:|---:|
| test_summary | 3891 | 3891 | 0 | 0 | 3891 |
| metadata_export | 3891 | 3891 | 0 | 0 | 3891 |
| test_detail | 3891 | 3891 | 0 | 0 | 3891 |
| vehicle_info | 3891 | 3891 | 0 | 1 | 3890 |
| barrier_info | 3891 | 3891 | 0 | 2264 | 1627 |
| occupant_info | 3891 | 3891 | 0 | 222 | 3669 |
| multimedia_files | 3891 | 3891 | 0 | 0 | 3891 |
| vehicle_documents | 3891 | 3891 | 0 | 0 | 3891 |
| intrusion_info | 4048 | 4048 | 0 | 3903 | 145 |
| restraint_info | 5618 | 5618 | 0 | 262 | 5356 |
| instrumentation_info | 25524 | 25524 | 0 | 26 | 25498 |

## Manifest Gate
- duplicate_test_no: 0
- pre_2011_rows: 0
- missing_test_date_rows: 0

## Endpoint Payload Distribution

| endpoint | payloads |
|---|---:|
| barrier_info | 3891 |
| instrumentation_info | 25524 |
| intrusion_info | 4048 |
| metadata_export | 3891 |
| multimedia_files | 3891 |
| occupant_info | 3891 |
| restraint_info | 5618 |
| test_detail | 3891 |
| test_summary | 3891 |
| vehicle_documents | 3891 |
| vehicle_info | 3891 |

## Runtime Collection Runs

| run_id | status | started_at | finished_at |
|---:|---|---|---|
| 1 | interrupted | 2026-04-30 12:15:49.925249 | 2026-04-30 13:51:36.952840 |
| 2 | interrupted | 2026-04-30 13:51:36.975057 | 2026-05-01 11:47:15.665257 |
| 3 | interrupted | 2026-05-01 11:47:15.673769 | 2026-05-02 04:18:02.923460 |
| 4 | succeeded | 2026-05-02 04:18:02.936479 | 2026-05-02 07:53:07.880416 |
| 5 | succeeded | 2026-05-02 07:59:17.249915 | 2026-05-02 08:31:31.832264 |

## Notes
- Empty successful payloads are recorded according to the endpoint matrix policy.
- File/media/package URLs were registered as metadata only; no file or media download was performed.
