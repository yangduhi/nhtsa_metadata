# 2026-05-02 | Classifier v1.4 Failure Package | RECORDED | v1.4 Full-Corpus Failure Package

## 목적

v1.4가 1500건 검증에서는 통과했지만 2011+ full corpus 3891건에서는 실패한 이유를 설명하기 위한 row-level 증거 패키지다.

## 원본 스냅샷

- classification JSON: `D:\vscode\nhtsa_metadata_runtime_archive\stage_d_2026-04-30\full_2011plus_classification_v1_4_2026-04-30.json`
- source DB: `D:\vscode\nhtsa_metadata_runtime_archive\stage_d_2026-04-30\full_2011plus_metadata_only_stage_d_2026-04-30.sqlite`
- 패키지 생성 중 live API 호출: false
- Stage D 분류에 사용된 rule file: `docs\us_fmvss_ncap_crash_test_classification_method_v1_4_1500sample_targeted_rules.json`

## 핵심 수량

- full corpus 전체 row: 3891
- classified row: 3844
- unclassified row: 47
- known false-positive row: 26
- failure manifest 전체 row: 73

## 포함 파일

- `failure_manifest_73.csv`: 47건 unclassified + 26건 known false-positive의 전달용 row-level 표.
- `failure_manifest_73.json`: 같은 73건을 nested evidence 구조까지 보존한 JSON.
- `2026-05-02__classifier-v1-4-failure-package__recorded__false-positive-check-definitions.md`: 실패한 false-positive check의 판정 조건, test_no 목록, 현재 rule, 기대 방향.
- `2026-05-02__classifier-v1-4-failure-package__recorded__feature-extraction-summary.md`: v1.4 feature 추출 방식 요약. directions, barrier/device types, speeds, angles, overlaps 등을 어디서 만드는지 확인용.
- `2026-05-02__classifier-v1-4-failure-package__recorded__full-scale-classification-v1-4-2011-plus.md`: full classification report 전문 복사본.
- `us_fmvss_ncap_crash_test_classification_method_v1_4_1500sample_targeted_rules.json`: Stage D에서 사용한 v1.4 rule file 복사본.
- `2026-05-02__classifier-v1-4-failure-package__recorded__full-scale-schema-audit-2011-plus.md`, `2026-05-02__classifier-v1-4-failure-package__recorded__full-scale-code-values-rebuild-2011-plus.md`, `2026-05-02__classifier-v1-4-failure-package__recorded__full-scale-endpoint-completeness-2011-plus.md`: 보조 Stage E 보고서.
- `package_file_index.json`: 패키지 파일별 byte size와 SHA-256 해시.

## 권장 확인 순서

1. `failure_manifest_73.csv`
2. `2026-05-02__classifier-v1-4-failure-package__recorded__false-positive-check-definitions.md`
3. `2026-05-02__classifier-v1-4-failure-package__recorded__full-scale-classification-v1-4-2011-plus.md`
4. `2026-05-02__classifier-v1-4-failure-package__recorded__feature-extraction-summary.md`
