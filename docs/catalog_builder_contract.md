# Catalog Builder Contract

Required CLI commands:

```powershell
python -m nhtsa_metadata.cli catalog discover --max-pages 1 --source fixture
python -m nhtsa_metadata.cli catalog collect-test --test-no 10001 --source fixture --endpoint-set all --paginate-instrumentation
python -m nhtsa_metadata.cli catalog collect --manifest tests/fixtures/live_sample_manifest.csv --source fixture
python -m nhtsa_metadata.cli catalog rebuild --test-no 10001
python -m nhtsa_metadata.cli coverage report
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
