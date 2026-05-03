# 2026-05-02 | Classifier v1.4 Failure Package | RECORDED | Feature Extraction Summary

## 코드 위치

- `src\nhtsa_metadata\services\rule_classifier.py`
- record loading: `_load_feature_records` lines `183-211`
- feature assembly: `_feature_record` lines `215-285`
- rule matching: `_matches_rule` lines `399-445`
- numeric/text helpers: `_number_tuple` lines `1104-1110`, `_expanded_angles` lines `1122-1143`, `_overlap_values` lines `1146-1154`, `_directions` lines `1157-1180`, `_barrier_types` lines `1183-1212`, `_device_types` lines `1215-1225`

## 추출 입력

- `text`: test number/reference, test type, configuration/key, title, performer, raw angle/offset/speed, vehicle make/model/engine/speed/weight, barrier rigidity/shape/angle, occupant/dummy, restraint/deployment, participant kind/name, media asset descriptor 최대 20개를 이어 붙여 normalize한다.
- `speeds_kmh`: `tests.closing_speed`와 vehicle speed에서 숫자값을 모아 unique/sorted tuple로 만든다.
- `masses_kg`: vehicle test weight 숫자값에서 만든다.
- `angles_deg`: test impact angle과 barrier angle을 기본으로 하고, side pole, 15-degree RMDB, 7-degree RMDB, side angle, 345/15-degree complement를 text 기반으로 확장한다.
- `overlaps_percent`: normalize된 전체 text에서 `OVERLAP=<n> PERCENT`, `<n> PERCENT OVERLAP`, `<n>% OVERLAP` 패턴만 숫자로 잡는다.
- `directions`: angle 범위와 `FRONT/FRONTAL`, `SIDE`, `REAR`, `OBLIQUE`, `ROLLOVER/FISHHOOK/SSF` 텍스트로 추론한다.
- `barrier_types`: text, barrier row, barrier participant에서 fixed rigid/collision barrier, MDB/RMDB/OMDB, pole 계열을 추론한다.
- `device_types`: `barrier_types`를 그대로 포함한 뒤 text에 따라 `sled`, `static_airbag`, `ejection_impactor`, `pedestrian_impactor`를 추가한다.

## 명시 feature로 없는 것

- `standards_detected`, `existing_family`, `title_pattern`은 v1.4 `feature_summary`에 별도 필드로 materialize되지 않는다.
- 현재는 normalize text match, candidate rules, rule families를 통해 간접 표현된다.

## 실패 해석에 중요한 신호

- known false-positive 26건은 evidence가 비어 있는 문제가 아니다. candidate가 존재하며, program/domain gate 또는 priority가 너무 넓어서 잘못 이긴 케이스다.
- unclassified 47건은 candidate list가 비어 있다. 즉 second-candidate ranking 문제가 아니라 rule coverage 또는 evidence gate gap이다.
