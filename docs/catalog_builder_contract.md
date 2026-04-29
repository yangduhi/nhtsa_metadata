# Catalog Builder Contract

이 프로젝트의 canonical/read-model 대상은 test_date >= 2011-01-01인 NHTSA crash test metadata로 제한한다.
modelYear는 scope 판단 기준이 아니다.
test_date missing 또는 parse 실패 record는 기본적으로 canonical/read-model에서 제외한다.

Required CLI commands:

```powershell
python -m nhtsa_metadata.cli catalog discover --max-pages 1 --source fixture
python -m nhtsa_metadata.cli catalog collect-test --test-no 10001 --source fixture --endpoint-set all --paginate-instrumentation
python -m nhtsa_metadata.cli catalog collect --manifest tests/fixtures/live_sample_manifest.csv --source fixture
python -m nhtsa_metadata.cli catalog build-manifest --source live --allow-live --output data/stratified_live_pilot_2011plus_manifest.csv --min-test-date 2011-01-01 --reference-database D:\vscode\pulse_analysis\data\db\nhtsa_data.db
python -m nhtsa_metadata.cli catalog rebuild --test-no 10001
python -m nhtsa_metadata.cli catalog rebuild
python -m nhtsa_metadata.cli coverage report
python -m nhtsa_metadata.cli schema audit --database-url sqlite:///data/stratified_live_pilot.sqlite --output data/schema_audit_report.json
python -m nhtsa_metadata.cli schema audit --include-duplicate-details --duplicate-detail-limit 50
```

Required options:

- `--dry-run`
- `--database-url`
- `--source fixture|live`
- `--allow-live`
- `--endpoint-set summary|metadata|detail|assets|all`
- `--paginate-instrumentation`
- `--save-fixture`
- `--stop-on-source-conflict`
- `--allow-empty-endpoints`
- `--retry-count`
- `--timeout-seconds`
- `--rate-limit-delay-seconds`
- `--resume`
- `--max-pages`
- `--max-items`
- `catalog build-manifest --min-test-date`
- `catalog build-manifest --reference-database`
- `schema audit --include-duplicate-details`
- `schema audit --duplicate-detail-limit`
