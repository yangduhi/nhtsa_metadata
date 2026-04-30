# Catalog Builder Contract

이 프로젝트의 canonical/read-model 대상은 `test_date >= 2011-01-01`인 NHTSA crash test metadata로 제한한다.
`modelYear`는 scope 판단 기준이 아니다.
`test_date` missing 또는 parse 실패 record는 기본적으로 canonical/read-model에서 제외한다.

## Required CLI Commands

```powershell
python -m nhtsa_metadata.cli catalog discover --max-pages 1 --source fixture
python -m nhtsa_metadata.cli catalog collect-test --test-no 10001 --source fixture --endpoint-set all --paginate-instrumentation
python -m nhtsa_metadata.cli catalog collect --manifest tests/fixtures/live_sample_manifest.csv --source fixture
python -m nhtsa_metadata.cli catalog build-manifest --source live --allow-live --output data/stratified_live_pilot_2011plus_manifest.csv --min-test-date 2011-01-01 --reference-database D:\vscode\pulse_analysis\data\db\nhtsa_data.db
python -m nhtsa_metadata.cli catalog rebuild --test-no 10001
python -m nhtsa_metadata.cli catalog rebuild
python -m nhtsa_metadata.cli coverage report
python -m nhtsa_metadata.cli schema audit --database-url sqlite:///data/stratified_live_pilot_2011plus.sqlite --output data/schema_audit_report_2011plus.json
python -m nhtsa_metadata.cli schema endpoint-completeness --manifest data/stratified_live_pilot_2011plus_manifest.csv --database-url sqlite:///data/stratified_live_pilot_2011plus.sqlite
python -m nhtsa_metadata.cli schema optimize-analyze --database-url sqlite:///data/stratified_live_pilot_2011plus.sqlite
python -m nhtsa_metadata.cli schema rebuild-code-values --database-url sqlite:///data/stratified_live_pilot_2011plus.sqlite
python -m nhtsa_metadata.cli schema backlog-triage --input data/schema_optimization_report.json
```

## Live Access Gate

Live API commands require all of:

- `--source live`
- `--allow-live`
- `NHTSA_METADATA_ALLOW_LIVE=true`

Default tests, `scripts/verify.ps1`, and `.harness/run.ps1` must remain fixture/mock only.

## Manifest Builder Requirements

- Use `testDateFrom=2011-01-01` for live by-search scope.
- Do not use `modelYearFrom` as scope.
- Do not use `test_no` ranges as scope.
- Support bounded manifests and explicit excluded manifests for expansion pilots.
- `--actual-crash-only` limits manifest rows to approved actual crash configurations.
- Summary links are not endpoint authority; endpoint templates and discovered request keys are authoritative.

## Canonical Rebuild Requirements

- Rebuild must preserve the 2011+ scope gate even when stored `source_payloads` include legacy rows.
- Rebuild must preserve occupant request context for occupant-scoped detail endpoints.
- Rebuild must keep full crawler and file download behavior outside the default command path.
- Rebuild must preserve raw/provenance lineage through `canonical_row_sources`.

## Schema v1.0 Derived Commands

`schema rebuild-code-values` is local-only and rebuilds the derived `code_values` registry from canonical/read-model tables. It must not call live APIs.

`schema backlog-triage` classifies local schema optimization output into v1.0 decisions. It must not call live APIs.
