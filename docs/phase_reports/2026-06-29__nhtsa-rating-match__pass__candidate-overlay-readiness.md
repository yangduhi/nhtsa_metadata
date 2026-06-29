# 2026-06-29 | NHTSA Rating Match | PASS | Candidate Overlay Readiness

상태: PASS
생성일: 2026-06-29
대상 DB: `D:/vscode/nhtsa_metadata/data/nhtsa_test_metadata_2011.sqlite`

## 1. 목적

메타데이터 DB의 subject vehicle row를 NHTSA 5-Star SafetyRatings API의 `VehicleId` 및 star rating 상세와 연결할 수 있는지, 실제 전체 DB 기준으로 read-only 후보 산출물을 생성해 검증했다.

초기 조사는 DB를 수정하지 않고 read-only URI로 수행했다. 이후 사용자 지시에 따라 원본
canonical/source row는 보존하고, 별도 overlay 테이블 `nhtsa_rating_match_candidates`만
생성/교체했다.

## 2. 추가된 스크립트

`D:/vscode/nhtsa_metadata/scripts/build_nhtsa_rating_match_candidates.py`

기능:

- `tests` + `test_participants` + `vehicles`에서 `participant_kind='subject_vehicle'` 기준 차량을 추출한다.
- NHTSA SafetyRatings API를 `--allow-live`가 있을 때만 호출한다.
- API 응답 cache를 저장해 재실행/검증 가능성을 높인다.
- candidate-level CSV, subject-level summary CSV, unmatched CSV, summary JSON을 생성한다.
- `--include-details` 사용 시 각 `VehicleId`의 star rating 상세 필드를 함께 저장한다.
- 복수 `VehicleId` 후보에는 가능한 경우 VIN/vPIC `BodyClass`, `Doors`, `DriveType`을 추가
  적용해 body/drive/cab variant를 재점수화한다.

대표 실행 명령:

```bash
python scripts/build_nhtsa_rating_match_candidates.py \
  --allow-live \
  --include-details \
  --outdir artifacts/nhtsa_rating_match \
  --progress-every 250
```

검증 명령:

```bash
python -m py_compile scripts/build_nhtsa_rating_match_candidates.py
uv run ruff check scripts/build_nhtsa_rating_match_candidates.py
```

결과:

- `py_compile`: PASS
- `ruff`: PASS (`All checks passed!`)

## 3. 생성/적용 산출물

최종 재생성 산출물 디렉터리: `D:/vscode/nhtsa_metadata/artifacts/nhtsa_rating_match_v8_deep`

주요 산출물:

| 파일 | 최종 row 수 | 설명 |
|---|---:|---|
| `candidate_rows.csv` | 6,076 | subject vehicle x SafetyRatings VehicleId 후보. Star rating 상세 포함. |
| `remaining_review_required.csv` | 373 | 자동 단일 선택을 보류해야 하는 복수 variant/review row. |
| `remaining_unmatched_or_not_key_ready.csv` | 895 | 후보 없음 또는 대상 부적합/key-not-ready row. |
| `report_enrichment_summary.json` | 22 applied | 공식 report evidence로 추가 확정한 row 요약. |
| `unresolved_deep_analysis_summary.json` | 373 review | 남은 review 원인 요약. |

주의: 위 CSV/JSON/PDF/text cache는 재생성 가능한 ignored artifact이며, durable 적용 상태는 SQLite overlay table `nhtsa_rating_match_candidates`에서 확인한다.

검증 결과:

- overlay table의 모든 6,076 candidate row에 `rating_vehicle_id`가 채워졌다.
- overlay table의 모든 6,076 candidate row에 `overall_rating`, `overall_front_crash_rating`, `overall_side_crash_rating`, `rollover_rating`이 채워졌다. 값은 숫자 별점 또는 `Not Rated`일 수 있다.
- DB의 subject vehicle denominator는 4,089 rows이며, SafetyRatings 후보 매칭 대상/비대상은 별도 상태로 분리했다.

## 4. Denominator 및 key readiness

전체 subject vehicle rows: 4,089

| 상태 | rows |
|---|---:|
| key_ready | 3,217 |
| matched_key_ready | 3,194 |
| unmatched_key_ready / no_safety_ratings_candidate | 23 |
| non_consumer_make (`NHTSA`, `OTHER`) | 860 |
| missing_or_zero_year | 12 |

Key-ready 조건:

- `model_year > 0`
- make 있음
- model 있음
- make가 `NHTSA`/`OTHER`가 아님

중요한 join 기준:

- `test_participants.vehicle_id`는 현재 DB에서 비어 있다.
- 실제 subject vehicle 연결은 `test_id + source_vehicle_no` 기준이다.
- Side MDB 등에서 `source_vehicle_no=1`이 deformable impactor인 경우가 있으므로, `vehicles.source_vehicle_no=1`을 무조건 subject로 보면 안 된다.

## 5. 매칭 성능

Key-ready subject vehicle 기준:

- matched: 3,194 / 3,217
- unmatched: 23 / 3,217
- match rate: 99.2850%

매칭 방법별 matched subject rows, `candidate_rank=1` 기준:

| method | rows |
|---|---:|
| direct | 2,777 |
| model_list_score_76 | 190 |
| model_list_score_100 | 137 |
| vpic_direct | 43 |
| model_list_score_86 | 38 |
| vpic_model_list_score_76 | 8 |
| vpic_model_list_score_100 | 1 |

## 6. Variant ambiguity

SafetyRatings API는 같은 year/make/model에 여러 `VehicleId` variant를 반환하는 경우가 많다.
NHTSA 공식 데이터/API 문서는 이를 오류로 보지 않고, 먼저 “available vehicle variants”를
반환한 뒤 “selected variant”의 `VehicleId`로 Safety Ratings를 조회하는 2-step flow로
정의한다. 공식 문서 표현상 `VehicleId`는 “precise model/required vehicle variant”를
조회하기 위한 식별자다.

Matched subject rows 3,194개 기준 variant count 분포:

| candidate variant count | subject rows |
|---:|---:|
| 1 | 1,171 |
| 2 | 1,701 |
| 3 | 45 |
| 4 | 160 |
| 5 | 5 |
| 6 | 96 |
| 7 | 1 |
| 8 | 15 |

요약:

- single-variant: 1,171 rows
- ambiguous multi-variant: 2,023 rows

따라서 “rating 후보 연결”은 높은 신뢰도로 가능하지만, “DB row에 단일 star rating 확정 부여”는 confidence/review queue가 필요하다.

Confidence 분포, `candidate_rank=1` 기준:

| confidence | rows |
|---|---:|
| HIGH_DISAMBIGUATED | 1,474 |
| HIGH_SINGLE_VARIANT | 1,171 |
| HIGH_EQUIVALENT_RATING | 115 |
| HIGH_TOP_EQUIVALENT_RATING | 39 |
| HIGH_REPORT_DISAMBIGUATED | 22 |
| REVIEW_AMBIGUOUS_VARIANT | 367 |
| MEDIUM_RANKED | 6 |

초기 body/vPIC scoring 이후 남은 406 review rows에 대해 vPIC 세부 필드와 공식 PDF report evidence를 추가 적용했다.
그 결과 review/medium은 406 → 373으로 감소했다. 남은 373건은 drive/release timing/cab/body-door 조합 등 공식 evidence만으로 단일 VehicleId를 단정하기 어려운 대상이다.

## 7. 대표 매칭 사례

### 7.1 모델명 정규화

- DB: `1993 CADILLAC DE VILLE`
- API model-list 후보: `DEVILLE`
- 결과: `1993 Cadillac Deville 4-DR.`
- confidence: `HIGH_SINGLE_VARIANT`

### 7.2 Ford F-150 표기 차이

- DB: `2011 FORD F150 SUPERCREW`
- API model-list 후보: `F-150 SUPER CREW`
- 결과 후보:
  - `2011 Ford F-150 Super Crew PU/CC 4x4`
  - `2011 Ford F-150 Super Crew PU/CC 4x2`
- 단일 선택에는 VIN/vPIC drive 또는 추가 review가 필요하다.

### 7.3 Lexus 숫자/공백 차이

- DB: `2011 LEXUS RX 350`
- API model-list 후보: `RX350`
- 결과 후보:
  - `2011 Lexus RX350 SUV AWD`
  - `2011 Lexus RX350 SUV FWD`

### 7.4 Toyota Tundra cab/drive variant

- DB: `2011 TOYOTA TUNDRA DOUBLE CAB`
- API 후보: `TUNDRA`
- 결과 후보 6개:
  - `PU/RC AWD`
  - `Double Cab AWD`
  - `PU/CC AWD`
  - `PU/RC RWD`
  - `Double Cab RWD`
  - `PU/CC RWD`
- DB 모델명으로 `Double Cab`까지 좁힐 수 있으나, AWD/RWD 단일 선택은 VIN/vPIC 보조가 필요하다.

## 8. 미매칭 row 성격

`per_subject_summary.csv` 기준 unmatched/non-matched reasons:

| reason | rows |
|---|---:|
| non_consumer_make | 949 |
| no_safety_ratings_candidate | 66 |
| missing_or_zero_year | 12 |
| missing_model | 1 |

`no_safety_ratings_candidate` 예시:

- `1996 SATURN SL1`
- `1997 NISSAN KING CAB PICKUP`
- `1998 DODGE AVENGER`
- `1998 VOLKSWAGEN BEETLE`
- `2010 FORD F150 PICKUP`
- `2011 DODGE RAM1500`
- `model='OTHER'` 또는 VIN 마스킹(`XXXX`)된 BMW/Infiniti/Mercedes/Acura 일부

## 9. 구현된 DB/API/GUI 적용 방식

source/canonical row는 직접 변경하지 않고 overlay 방식을 적용했다.

구현 테이블: `nhtsa_rating_match_candidates`

주요 컬럼:

- `test_no`
- `source_vehicle_no`
- `db_make`, `db_model`, `db_model_year`, `db_body_style`, `db_vin`
- `match_method`
- `match_confidence`
- `query_make`, `query_model`
- `rating_vehicle_id`
- `rating_vehicle_description`
- `candidate_rank`
- `candidate_score`
- `variant_count`
- `generated_at`

현재 DB 적재 결과, 2026-06-29 v8_deep 기준:

- table: `nhtsa_rating_match_candidates`
- generated_at: `2026-06-29T12:17:40+00:00`
- candidate rows: 6,076
- matched subject rows: 3,194
- ambiguous subject rows: 2,023
- auto-selected/equivalent/report-evidence subject rows: 2,821
- review required subject rows: 373

confidence breakdown, `candidate_rank=1` 기준:

| confidence | subject rows |
|---|---:|
| `HIGH_DISAMBIGUATED` | 1,474 |
| `HIGH_SINGLE_VARIANT` | 1,171 |
| `HIGH_EQUIVALENT_RATING` | 115 |
| `HIGH_TOP_EQUIVALENT_RATING` | 39 |
| `HIGH_REPORT_DISAMBIGUATED` | 22 |
| `REVIEW_AMBIGUOUS_VARIANT` | 367 |
| `MEDIUM_RANKED` | 6 |

구현 API:

- `GET /api/safety-ratings/summary`
- `GET /api/safety-ratings/tests/{test_no}`
- `GET /api/tests/{test_no}` detail payload의 `safety_rating_match`

구현 GUI:

- `/metadata-refresh`에 `NHTSA SafetyRatings overlay` 패널 추가
- matched subjects, candidate rows, review required, official handling 카드 표시
- browser smoke에서 `matched subjects=3,194`, `candidate rows=6,076`, `review required=373` 카드 표시와 console error 0건 확인

향후 확장 권장 테이블: `nhtsa_rating_match_selection`

주요 컬럼:

- `test_no`
- `source_vehicle_no`
- `selected_rating_vehicle_id`
- `selection_status`: `auto_high`, `manual_approved`, `review_required`, `rejected`
- `selection_reason`
- `review_notes`
- `approved_at`

## 10. 적용 정책

사용자 지시에 따라 overlay + API + GUI 표시까지 연결했다. selection 상태는 다음처럼 노출한다.

- `HIGH_SINGLE_VARIANT` → `auto_selected_single_variant`
- `HIGH_DISAMBIGUATED` → `auto_high_candidate`
- `HIGH_REPORT_DISAMBIGUATED` → `auto_report_evidence`
- `HIGH_EQUIVALENT_RATING` → `auto_equivalent_rating`
- `HIGH_TOP_EQUIVALENT_RATING` → `auto_top_equivalent_rating`
- `MEDIUM_RANKED` → `ranked_candidate_reviewable`
- `REVIEW_AMBIGUOUS_VARIANT` → `review_required`

## 11. v8_deep 추가 분석 결과

초기 overlay 이후 사용자가 요청한 심층 분석을 수행해 review를 추가 축소했다.

- 이전 v7 review/medium: 406
- 최종 v8_deep review/medium: 373
- 추가 감소: 33
  - vPIC 세부 필드 보강: 11건
  - NHTSA 공식 report PDF evidence: 22건
- 후보 없음/대상 부적합/key-not-ready: 895건은 강제 매핑하지 않고 review/non-mutation scope로 동결

공식/원자료 사용:

- NHTSA SafetyRatings modelyear/make/model API
- NHTSA SafetyRatings VehicleId API
- NHTSA vPIC DecodeVinValues API
- NHTSA SafetyRatings model-list API
- NHTSA 공식 report PDF under `nrd-static.nhtsa.dot.gov`

대표 `HIGH_REPORT_DISAMBIGUATED` 검증 사례:

- 8057 → 2013 Infiniti JX SUV AWD
- 9351 → 2016 Hyundai Tucson SUV FWD
- 10383 → 2018 Tesla Model 3 4 DR RWD
- 14248 → 2022 Toyota TUNDRA PU/CC 4WD
- 15074 → 2024 Chevrolet Blazer EV SUV AWD

## 12. 결론

메타데이터 DB와 NHTSA SafetyRatings는 subject vehicle 기준으로 높은 수준의 후보 매칭이 가능하다.

- key-ready subject vehicle 3,217개 중 3,194개가 후보 매칭됨.
- star rating 상세까지 포함한 candidate rows 6,076개를 생성하고 DB overlay에 적재했다.
- 자동 확정/equivalent/report-evidence 처리 가능한 subject rows는 2,821개다.
- 남은 373건은 공식 NHTSA VehicleId variant가 복수이고 DB/vPIC/PDF evidence만으로 단일 VehicleId를 단정하면 오매핑 위험이 있는 review 대상이다.
- `/api/safety-ratings/summary`, `/api/safety-ratings/tests/{test_no}`, `/api/tests/{test_no}` 및
  `/metadata-refresh` GUI에서 overlay를 확인할 수 있다.

다음 단계가 필요하다면 `review_required` 373건에 대한 manual review/selection workflow를 추가한다.
