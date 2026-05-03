# 2026-05-02 | Classifier v1.4 Failure Package | RECORDED | False-Positive Check Definitions

## 원본 위치

- code: `src\nhtsa_metadata\services\rule_classifier.py:_known_false_positive_checks`
- side pole check source lines: `912-921`
- sled check source lines: `955-958`
- row-level evidence: `failure_manifest_73.csv` / `failure_manifest_73.json`

## side pole over-confirmed without program keyword

- count: 8
- test_no: `10841`, `10842`, `10845`, `11600`, `11604`, `14354`, `14355`, `14604`
- 판정 조건: `canonical_rule_id`가 `US_NCAP_SIDE_POLE_20MPH_75DEG_25CM` 또는 `FMVSS_214_SIDE_POLE_20MPH_75DEG_254MM`인데, row text에 `NCAP`, `NEW CAR ASSESSMENT`, `FMVSS 214`, `FMVSS214`, `571.214` 중 어느 것도 없으면 fail이다.
- 현재 matched_rule_id: 8건 모두 `US_NCAP_SIDE_POLE_20MPH_75DEG_25CM`.
- 현재 candidate 구조: 8건 모두 top candidate는 `US_NCAP_SIDE_POLE_20MPH_75DEG_25CM`, second candidate는 `RESEARCH_VEHICLE_INTO_POLE_GENERIC_SIDE_POLE`.
- 기대 classification/domain: `NHTSA_RESEARCH_OR_SIDE_POLE_MANUAL_REVIEW`.
- 기대 rule if known: `RESEARCH_VEHICLE_INTO_POLE_GENERIC_SIDE_POLE`.
- 권장 조치: NCAP/FMVSS 214 side-pole protocol rule에는 명시적 program/standard evidence를 요구하거나, `test_type=RESEARCH`에서는 research/generic pole rule이 이기도록 gate/priority를 조정해야 한다.

## sled test classified as full vehicle crash

- count: 18
- test_no: `9230`, `9231`, `9232`, `9233`, `9234`, `9235`, `9236`, `9237`, `9238`, `9239`, `9240`, `9241`, `9242`, `9243`, `9244`, `9245`, `9246`, `9247`
- 판정 조건: row text에 `SLED`가 있고 `classification_status=classified`인데 `canonical_rule_id`에 `SLED`가 없으면 fail이다.
- 현재 matched_rule_id: 17건은 `NHTSA_RESEARCH_FRONTAL_OBLIQUE_RMDB_LEGACY_OR_MATRIX`, 1건은 `NHTSA_RESEARCH_FRONTAL_OBLIQUE_OMDB_90KPH_15DEG_35PCT_THOR50M`.
- 현재 candidate 구조: 모든 row에 `GENERIC_SLED_TEST_UNKNOWN_SUBTYPE` 후보가 있으나 full-vehicle oblique RMDB/OMDB 계열 rule보다 낮은 우선순위로 밀린다.
- 기대 classification/domain: `NHTSA_RESEARCH_SLED_WITH_VEHICLE_BODY`.
- 기대 rule if known: `GENERIC_SLED_TEST_UNKNOWN_SUBTYPE_OR_TARGETED_SLED_WITH_BODY_OBLIQUE_RULE`.
- 권장 조치: `SLED WITH VEHICLE BODY` domain gate/priority를 추가해 full-vehicle oblique RMDB/OMDB rule이 sled rule을 이기지 못하게 해야 한다.

## Row-Level 확인 위치

각 row의 `test_date`, `test_type`, `test_configuration`, `test_configuration_key`, `contractor_study_title`, 현재 matched rule, candidate top5, `feature_summary`, `matched_evidence_json`은 `failure_manifest_73.csv`와 `failure_manifest_73.json`에 포함되어 있다.
