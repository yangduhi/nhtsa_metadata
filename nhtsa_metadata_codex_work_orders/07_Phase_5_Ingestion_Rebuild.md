# Phase 5 — Ingestion / Rebuild 작업지시서

## 목표

Fixture/source client payload를 DB에 저장하고, parser/mapper 결과를 canonical tables에 idempotent하게 upsert한다. 또한 raw payload에서 canonical/read-model을 재생성하는 rebuild flow를 구현한다.

## 범위

구현 대상:

```text
source payload 저장
source payload observation 저장
source section 저장
field catalog upsert
canonical row upsert
canonical_row_sources 저장
source_conflicts 저장
read model rebuild
catalog CLI 확장
coverage report CLI
fixture client 기반 collect-test/collect/rebuild 테스트
```

Live HTTP client는 safety skeleton 또는 fake transport까지만 구현한다. 실제 manual live command 완성은 Phase 7.

## 생성/수정 파일

```text
src/nhtsa_metadata/services/source_payload_service.py
src/nhtsa_metadata/services/field_catalog_service.py
src/nhtsa_metadata/services/ingestion_service.py
src/nhtsa_metadata/services/canonical_upsert.py
src/nhtsa_metadata/services/conflict_service.py
src/nhtsa_metadata/services/read_model_builder.py
src/nhtsa_metadata/services/coverage_service.py
src/nhtsa_metadata/services/catalog_builder.py
src/nhtsa_metadata/cli.py

tests/test_source_payload_service.py
tests/test_field_catalog_service.py
tests/test_ingestion_idempotency.py
tests/test_catalog_builder_fixture.py
tests/test_rebuild.py
tests/test_coverage_report.py

docs/phase_reports/2026-04-28__bootstrap-phase-5__pass__phase-5-report.md
```

## SourcePayloadService

```python
class SourcePayloadService:
    def save_payload(self, fetch_result: SourceFetchResult, run_id: int | None, run_item_id: int | None) -> SourcePayload:
        ...

    def save_sections(self, source_payload_id: int, sections: list[SectionObservation]) -> None:
        ...

    def get_latest_payloads_for_test(self, test_no: int, endpoint_names: list[str] | None = None) -> list[SourcePayload]:
        ...
```

규칙:

- `canonical_url_hash`는 normalized request URL에서 계산.
- `payload_hash`는 full JSON payload에서 계산.
- `source_payloads`는 `(endpoint_name, canonical_url_hash, payload_hash)`로 upsert.
- fetch 이벤트마다 `source_payload_observations`는 항상 insert.
- pagination fields 저장.
- empty endpoint도 정상 payload로 저장.

## FieldCatalogService

```python
class FieldCatalogService:
    def record_observations(self, observations: Iterable[FieldObservation]) -> None:
        ...

    def snapshot(self, run_id: int | None = None) -> FieldCoverageSnapshot:
        ...
```

규칙:

- unique key: `endpoint_name + section_name + field_path`
- `seen_count` 증가.
- non-null이면 `non_null_count` 증가.
- `first_seen_at` 보존.
- `last_seen_at` 갱신.
- example values는 최대 5개 저장.

## Canonical upsert

구현 함수:

```python
upsert_test(spec)
upsert_vehicle(test_id, spec)
upsert_barrier(test_id, spec)
upsert_participant(test_id, spec)
upsert_occupant(test_id, vehicle_id, spec)
upsert_restraint(test_id, vehicle_id, occupant_id, spec)
upsert_instrumentation_channel(test_id, vehicle_id, occupant_id, spec)
upsert_injury_metric(test_id, vehicle_id, occupant_id, spec)
upsert_deformation_measurement(test_id, vehicle_id, spec)
upsert_intrusion_measurement(test_id, vehicle_id, spec)
upsert_media_asset(test_id, spec)
upsert_code_value(code_set, code_value, ...)
```

규칙:

- Phase 2 natural keys 사용.
- 같은 natural key + 같은 source hash는 중복 생성 금지.
- 같은 natural key + source hash 변경 시 update.
- upsert 후 `canonical_row_sources` association 작성.
- `raw_row_json`, `extra_json`, lineage 보존.

## ConflictService

Semantic conflict 최소 키:

```text
tests.test_date_raw
tests.closing_speed
tests.test_configuration
vehicles.make
vehicles.model
vehicles.model_year
barriers.rigidity
barriers.shape
```

규칙:

- 서로 다른 endpoint가 같은 semantic key에 대해 다른 non-empty 값을 주면 unresolved conflict 저장.
- 기본적으로 실패시키지 않는다.
- `--stop-on-source-conflict`가 있으면 current item abort.

## ReadModelBuilder

```python
class ReadModelBuilder:
    def rebuild_test(self, test_id: int) -> None:
        ...

    def rebuild_all(self) -> None:
        ...
```

Build:

```text
test_filter_summary
test_facets
asset_summary
```

Facet emission:

```text
test_type
test_configuration
vehicle_make
vehicle_model
model_year
closing_speed_range
impact_angle
participant_kind
barrier_rigidity
barrier_shape
occupant_location
dummy_type
restraint_type
restraint_deployment
sensor_type
sensor_location
sensor_attachment
sensor_axis
sensor_unit
injury_metric_code
injury_metric_range
deformation_code
asset_kind
has_uds_or_tdms_package
```

Range bucket v1 예:

```text
closing_speed: 0-10, 10-25, 25-40, 40-55, 55-70, 70+, unknown
injury_metric_range: exact numeric은 canonical에서, bucket facet은 optional
```

## CatalogBuilder

```python
class CatalogBuilder:
    def discover(...): ...
    def collect_test(test_no: int, endpoint_set: str, paginate_instrumentation: bool, source: str) -> CollectResult: ...
    def collect_manifest(manifest_path: Path, ...) -> CollectManifestResult: ...
    def rebuild_test(test_no: int, rebuild_read_models: bool = True) -> RebuildResult: ...
```

Endpoint collection order:

```text
1. test_summary
2. metadata_export
3. test_detail optional
4. vehicle_info
5. vehicle_detail per vehicle optional
6. barrier_info
7. occupant_info
8. occupant_detail per occupant optional
9. restraint_info per occupant
10. intrusion_info per vehicle
11. instrumentation_info all pages
12. instrumentation_detail optional/per curve when explicitly requested
13. multimedia_files
14. vehicle_documents
```

기본 v1에서는 instrumentation detail for every curve를 자동 호출하지 않는다.

## CLI

필수 commands:

```powershell
python -m nhtsa_metadata.cli catalog discover --max-pages 1 --source fixture
python -m nhtsa_metadata.cli catalog collect-test --test-no 10001 --source fixture --endpoint-set all --paginate-instrumentation
python -m nhtsa_metadata.cli catalog collect --manifest tests/fixtures/live_sample_manifest.csv --source fixture
python -m nhtsa_metadata.cli catalog rebuild --test-no 10001 --database-url sqlite:///data/nhtsa_metadata.sqlite
python -m nhtsa_metadata.cli coverage report --database-url sqlite:///data/nhtsa_metadata.sqlite
```

필수 options:

```text
--dry-run
--database-url
--source fixture|live
--allow-live
--endpoint-set summary|metadata|detail|assets|all
--paginate-instrumentation / --no-paginate-instrumentation
--save-fixture
--stop-on-source-conflict
--allow-empty-endpoints / --no-allow-empty-endpoints
--retry-count
--timeout-seconds
--rate-limit-delay-seconds
--resume
--max-pages
--max-items
```

Live safety:

```text
source == live and allow_live == false -> UsageError
source == live and settings.allow_live == false and env not set -> UsageError
source == fixture -> no network
```

## Dry-run

`--dry-run`:

- manifest/test list resolve.
- endpoint matrix resolve.
- planned operations print.
- DB insert 없음.
- 권장: collection_runs도 생성하지 않음.

## Resume

`--resume`:

- 동일 manifest hash/endpoint_set의 incomplete run 탐색.
- succeeded item skip.
- failed/partial/pending retry.
- v1은 단순 구현 허용: 같은 DB에서 이미 succeeded인 test_no skip.
- limitation은 문서화.

## Rebuild

`catalog rebuild --test-no 10001`:

1. source_payloads load.
2. 해당 test canonical rows dependency order로 삭제.
3. stored payload parser/mapper 재실행.
4. canonical upsert.
5. read model rebuild.
6. counts 출력.

주의:

- source_payloads 삭제 금지.
- rebuild도 collection_runs에 기록 가능.

## 테스트

### Source payload

- save once -> source_payloads 1, observations 1.
- same payload again -> source_payloads 1, observations 2.
- changed payload -> source_payloads 2.
- empty results 저장.

### Idempotency

- 10001 fixture ingest.
- table counts 기록.
- 동일 fixture ingest 재실행.
- canonical/read-model counts 불변. run/observation counts 증가는 허용.

### Catalog builder

- collect-test 10001 -> test/vehicle/barrier/occupant/restraint/instrumentation/media rows.
- collect-test 10003 -> 2 vehicles + impactor participant.
- empty barrier endpoint failure 아님.
- dry-run no rows.

### Rebuild

- collect 10001.
- canonical/read-model counts capture.
- 일부 canonical row 삭제.
- rebuild from source_payloads.
- counts restored.

### Coverage report

- mapped/unmapped fields 존재.
- CLI report 성공.

## 완료 기준

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check src tests
.venv\Scripts\python.exe -m mypy src\nhtsa_metadata
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
powershell -ExecutionPolicy Bypass -File .harness\run.ps1
```

추가 조건:

```text
fixture collect-test works for 10001 and 10003
same fixture re-collection does not duplicate canonical rows
raw source_payloads remain available
rebuild from raw source_payloads works
field coverage report works
live source cannot run without --source live --allow-live
```
