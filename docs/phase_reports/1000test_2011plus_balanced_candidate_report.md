# 1000-Test 2011+ Balanced Candidate Report

## 결론

- reference DB 기반 1000건 후보군을 생성했다.
- live manifest build, live collect, full crawler, 파일 다운로드는 실행하지 않았다.
- 후보군은 `test_date >= 2011-01-01`, 중복 없음, anchor `7201/10001/10003` 포함 조건을 만족한다.
- 연도 배분은 2011~2025 기준 quota와 실제 선택 수가 정확히 일치한다.
- 2026년은 reference DB에 eligible row가 0건이라 후보군에 포함할 수 없으며, live by-search 단계에서 별도 확인 대상이다.
- 시험종류 배분은 연도 quota를 hard constraint로 고정한 상태에서 가능한 최대 편차를 최소화했고, 모든 available 시험종류를 최소 1건 이상 포함했다.

## Scope

- 기준 범위: `2011-01-01 <= test_date <= 2026-12-31`.
- scope 판단 기준: `test_date`; `modelYear`는 사용하지 않음.
- seed source: `D:\vscode\pulse_analysis\data\db\nhtsa_data.db`.
- output candidate: `data/stratified_live_pilot_2011plus_1000_balanced_candidate.csv`.
- 이 CSV는 ignored data artifact이며 Git 커밋 대상이 아니다.

## Reference DB Summary

| 항목 | 값 |
|---|---:|
| `crash_tests` total | 4513 |
| parseable `test_date` rows | 4344 |
| pre-2011 parseable rows | 456 |
| missing `test_date` rows | 169 |
| date parse failed rows | 0 |
| 2011~2026 eligible rows | 3888 |
| 2026 eligible rows | 0 |

## Candidate Acceptance

| 확인 항목 | 결과 |
|---|---:|
| selected rows | 1000 |
| duplicate `test_no` | 0 |
| date range | 2011-01-03 ~ 2025-09-23 |
| `scope_status=in_scope` | 1000 |
| 7201 included | True |
| 10001 included | True |
| 10003 included | True |
| max year quota deviation | 0 |
| max configuration quota deviation | 13 |
| sum configuration absolute deviation | 182 |

## Selection Method

- 2011+ reference DB rows 중 `test_date`가 parse 가능하고 범위 내인 row만 후보로 사용했다.
- `7201`, `10001`, `10003`은 anchor로 고정 포함했다.
- 2026년 row가 없어 2011~2025 available years에 1000건 quota를 water-fill 방식으로 배분했다.
- 시험종류 quota도 availability cap을 고려해 water-fill 방식으로 계산했다.
- 최종 선택은 연도 quota를 hard constraint로 두고, 시험종류별 최대 편차를 최소화하는 flow 기반 선택으로 생성했다.
- 각 available 시험종류는 최소 1건 이상 포함되도록 제한했다.

## Year Distribution

| year | reference available | quota | selected | deviation |
|---:|---:|---:|---:|---:|
| 2011 | 345 | 67 | 67 | 0 |
| 2012 | 434 | 67 | 67 | 0 |
| 2013 | 470 | 67 | 67 | 0 |
| 2014 | 360 | 67 | 67 | 0 |
| 2015 | 249 | 67 | 67 | 0 |
| 2016 | 412 | 67 | 67 | 0 |
| 2017 | 321 | 67 | 67 | 0 |
| 2018 | 205 | 67 | 67 | 0 |
| 2019 | 185 | 67 | 67 | 0 |
| 2020 | 226 | 67 | 67 | 0 |
| 2021 | 170 | 66 | 66 | 0 |
| 2022 | 118 | 66 | 66 | 0 |
| 2023 | 164 | 66 | 66 | 0 |
| 2024 | 156 | 66 | 66 | 0 |
| 2025 | 73 | 66 | 66 | 0 |
| 2026 | 0 | 0 | 0 | 0 |

## Test Configuration Distribution

| configuration_key | configuration | reference available | quota | selected | deviation |
|---|---|---:|---:|---:|---:|
| FCW_PERFORMANCE | FORWARD COLLISION WARNING PERFORMANCE TEST | 45 | 45 | 35 | -10 |
| IMPACTOR_INTO_IMPACTOR | IMPACTOR INTO IMPACTOR | 6 | 6 | 1 | -5 |
| ITV | IMPACTOR INTO VEHICLE | 810 | 90 | 103 | 13 |
| LDW_PERFORMANCE | LANE DEPARTURE WARNING PERFORMANCE TEST | 31 | 31 | 18 | -13 |
| LRD | LOW RISK DEPLOYMENT | 261 | 90 | 103 | 13 |
| OTHER | OTHER | 21 | 21 | 8 | -13 |
| PEDESTRIAN | PEDESTRIAN | 195 | 90 | 77 | -13 |
| ROLLOVER | ROLLOVER | 130 | 90 | 77 | -13 |
| SLED_NO_BODY | SLED WITHOUT VEHICLE BODY | 565 | 90 | 103 | 13 |
| SLED_WITH_BODY | SLED WITH VEHICLE BODY | 156 | 90 | 103 | 13 |
| STATIC_SIDE_AIRBAG | STATIC AIR BAG TEST SIDE | 235 | 90 | 103 | 13 |
| TRAFFIC_JAM_ASSIST | TRAFFIC JAM ASSIST | 1 | 1 | 1 | 0 |
| UNKNOWN | UNKNOWN | 76 | 76 | 63 | -13 |
| VTB | VEHICLE INTO BARRIER | 729 | 89 | 102 | 13 |
| VTP | VEHICLE INTO POLE | 615 | 89 | 102 | 13 |
| VTV | VEHICLE INTO VEHICLE | 12 | 12 | 1 | -11 |

## Candidate Columns

- `test_no`, `test_date`, `test_year`, `year_quota`.
- `test_configuration_key`, `configuration_quota`, `test_configuration`, `test_family`.
- `stratum_key`, `stratum_available_count`, `stratum_selected_count`.
- `classification_status`, `reason`, `scope_status`, `seed_source`, `anchor_flag`, `selection_round`.
- expected endpoint/media/restraint/instrumentation hints and reference make/model/year/count fields.

## Not Executed

- NHTSA live by-search manifest build: 미실행.
- 1000건 live collect: 미실행.
- full crawler: 미실행.
- 파일 다운로드 및 media URL fetch: 미실행.
- waveform/TDMS/UDS/EV/ABF/ISO/ZIP 내부 분석: 미실행.

## Next Decision Gate

- 이 후보군은 live canonical source가 아니라 reference DB seed 후보군이다.
- 다음 단계는 별도 승인 후 live by-search로 1000건 manifest를 검증하거나 재생성하는 것이다.
- live collect는 manifest review 통과 후 별도 승인으로 분리해야 한다.
- 2026년 row 필요 여부는 live by-search에서 확인해야 하며, 현재 reference DB만으로는 2026년 후보를 만들 수 없다.
