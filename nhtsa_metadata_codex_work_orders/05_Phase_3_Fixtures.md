# Phase 3 — Fixtures 작업지시서

## 목표

fixture/mock 기반으로 NHTSA source shape를 재현한다. 기본 test suite에서 live API를 호출하지 않고 legacy, modern, multi-vehicle, pagination, media/document variation을 검증할 수 있어야 한다.

## Fixture 범위

최소 test_no:

```text
10      legacy VTB; metadata export contains TEST/VEHICLE/BARRIER/OCCUPANT
30      legacy NCAP VTB; zero injury metrics; report/video no photos
10001   modern frontal NCAP; 1 vehicle; barrier; 2 occupants; instrumentation/media/data packages
10003   modern side impact; 2 vehicles; impactor-as-vehicle; no barrier endpoint data; instrumentation/media/report
```

Live validation manifest에는 추가로 `1`, `10004`, `10005`도 포함한다.

## 생성할 파일

```text
tests/fixtures/nhtsa/fixture_manifest.json
tests/fixtures/nhtsa/live_sample_manifest.csv

tests/fixtures/nhtsa/metadata_10.json
tests/fixtures/nhtsa/metadata_30.json
tests/fixtures/nhtsa/metadata_10001.json
tests/fixtures/nhtsa/metadata_10003.json

tests/fixtures/nhtsa/test_summary_10001.json
tests/fixtures/nhtsa/test_summary_10003.json

tests/fixtures/nhtsa/vehicle_info_10001.json
tests/fixtures/nhtsa/vehicle_info_10003.json

tests/fixtures/nhtsa/barrier_info_10001.json
tests/fixtures/nhtsa/barrier_info_10003_empty.json

tests/fixtures/nhtsa/occupant_info_10001.json
tests/fixtures/nhtsa/occupant_info_10003.json

tests/fixtures/nhtsa/restraint_info_10001_left_front_seat.json
tests/fixtures/nhtsa/restraint_info_10001_right_front_seat.json

tests/fixtures/nhtsa/intrusion_info_10001_empty.json
tests/fixtures/nhtsa/instrumentation_info_10001_page_0.json
tests/fixtures/nhtsa/instrumentation_info_10001_page_1.json
tests/fixtures/nhtsa/instrumentation_info_10003_page_0.json

tests/fixtures/nhtsa/multimedia_files_10001.json
tests/fixtures/nhtsa/multimedia_files_10003.json
tests/fixtures/nhtsa/vehicle_documents_10001.json
tests/fixtures/nhtsa/vehicle_documents_10003.json
```

일부 fixture는 compact seed + deterministic generator로 대체 가능하다.

```text
tests/fixtures/nhtsa/generated/instrumentation_10001_seed.json
src/nhtsa_metadata/sources/nhtsa_crash/fixture_factory.py
```

## 공통 API-style fixture wrapper

```json
{
  "meta": {
    "pagination": {
      "pageNumber": 0,
      "count": 1,
      "total": 1,
      "currentUrl": "http://...",
      "nextUrl": null,
      "previousUrl": null
    },
    "status": 200,
    "message": "Success",
    "error": ""
  },
  "results": []
}
```

`metadata/{testNo}` export fixture는 실제 shape에 맞춰 `TEST`, `VEHICLE`, `BARRIER`, `OCCUPANT`, `RESTRAINT`, `INSTRUMENTATION`, `URL`, `REPORTS`, `VIDEOS`, `PHOTOS` section을 포함할 수 있다.

## `fixture_manifest.json`

endpoint key와 fixture file을 연결한다.

예:

```json
{
  "tests": {
    "10001": {
      "test_summary": "test_summary_10001.json",
      "metadata_export": "metadata_10001.json",
      "vehicle_info": "vehicle_info_10001.json",
      "barrier_info": "barrier_info_10001.json",
      "occupant_info": "occupant_info_10001.json",
      "restraint_info": {
        "1|LEFT FRONT SEAT": "restraint_info_10001_left_front_seat.json",
        "1|RIGHT FRONT SEAT": "restraint_info_10001_right_front_seat.json"
      },
      "intrusion_info": {
        "1": "intrusion_info_10001_empty.json"
      },
      "instrumentation_info": [
        "instrumentation_info_10001_page_0.json",
        "instrumentation_info_10001_page_1.json"
      ],
      "multimedia_files": "multimedia_files_10001.json",
      "vehicle_documents": "vehicle_documents_10001.json"
    }
  }
}
```

## `live_sample_manifest.csv`

```csv
test_no,reason
1,early legacy record; basic listing/detail shape
10,legacy VTB; metadata export contains TEST/VEHICLE/BARRIER/OCCUPANT
30,legacy NCAP VTB; zero injury metrics; report/video no photos
10001,modern frontal NCAP; 1 vehicle; barrier; 2 occupants; 634 instrumentation channels; many media/data packages
10003,modern side impact; 2 vehicles; impactor-as-vehicle; no barrier endpoint data; 63 instrumentation channels
10004,media-heavy modern test
10005,media-heavy modern test
```

## Fixture content 요구사항

### `metadata_10.json`

필수 section:

```text
TEST
VEHICLE
BARRIER
OCCUPANT
```

필수 field:

```text
TEST.TSTNO = 10
TEST.TSTDAT = legacy date string
TEST.TSTCFND = VEHICLE INTO BARRIER 또는 equivalent
VEHICLE.MAKED = PLYMOUTH
VEHICLE.MODELD = FURY
VEHICLE.YEAR = 1975
BARRIER.BARRIGD = DEFORMABLE 또는 RIGID 등 fixture 목적에 맞는 값
OCCUPANT.OCCLOC = LEFT FRONT SEAT / RIGHT FRONT SEAT
OCCUPANT.HIC = non-zero value
```

### `metadata_30.json`

zero/null/missing 구분용.

```text
OCCUPANT.HIC = 0 또는 "0"
OCCUPANT.LFEM = 0 또는 "0"
일부 optional metric = null
일부 field = missing
```

### `test_summary_10001.json`

필수 anomaly:

```text
testNo = 10001
testType = NEW CAR ASSESSMENT TEST
testDate = 2016-12-12
testConfiguration = VEHICLE INTO BARRIER
closingSpeed = 56.11
vehicleInformation = .../get-vehicle-info/10001
barrierInformation = .../get-vehicle-info/10001    # wrong link anomaly
instrumentationInformation = .../get-instrumentation-info/10001
documentInformation = .../vehicle-documents/test-no/10001
```

### `vehicle_info_10003.json`

```text
results length = 2
row 1: vehicleNo=1, vehicleMake=NHTSA, vehicleModel=DEFORMABLE IMPACTOR
row 2: vehicleNo=2, vehicleMake=CHEVROLET, vehicleModel=VOLT
```

### `barrier_info_10003_empty.json`

정상 status + empty results.

```json
{
  "meta": {"pagination": {"pageNumber": 0, "count": 0, "total": 0}, "status": 200, "message": "Success", "error": ""},
  "results": []
}
```

### `instrumentation_info_10001_page_*.json`

```text
page 0: pageNumber=0, count=20, total=634, nextUrl not null
page 1: pageNumber=1, total=634
```

테스트 목적상 실제 row는 40개만 저장해도 된다. 단, pagination/volume 테스트에서는 generator로 634개 canonical channel을 만들 수 있어야 한다.

### Media/documents

`multimedia_files_10001.json`은 photo/video/report를 포함한다. `vehicle_documents_10001.json`은 uds, abf, iso zip, tdms zip, other zip 또는 유사 data package URL을 포함한다. 실제 다운로드는 금지한다.

## Fixture client

생성/수정:

```text
src/nhtsa_metadata/sources/nhtsa_crash/fixtures.py
src/nhtsa_metadata/sources/nhtsa_crash/fixture_factory.py
```

동작:

```python
client.fetch(endpoint_name="test_summary", test_no=10001)
client.fetch(endpoint_name="instrumentation_info", test_no=10001, page_number=0)
client.fetch_all_pages(endpoint_name="instrumentation_info", test_no=10001)
```

요구사항:

- filesystem fixture 로드.
- missing fixture는 `FixtureNotFoundError`.
- 외부 HTTP 호출 금지.
- `fixture_manifest.json` 기반 endpoint/test_no/page mapping.
- generated fixture는 deterministic.

## Network guard

기본 tests에서 accidental network call이 발생하면 실패하게 한다.

예:

```python
@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("External network call is not allowed in default tests")
    monkeypatch.setattr(httpx.Client, "request", fail)
```

Live client test는 respx/fake transport만 사용한다.

## 테스트

```text
tests/test_fixtures.py
tests/test_fixture_client.py
```

검증:

- 모든 fixture JSON parse 가능.
- live_sample_manifest.csv column과 test_no 확인.
- 10001 summary fixture가 wrong barrierInformation link 포함.
- 10003 vehicle fixture가 2 rows 포함.
- 10003 barrier empty fixture가 failure로 간주되지 않음.
- 30 fixture가 zero/null/missing 포함.
- fixture client가 외부 HTTP 없이 payload 반환.
- instrumentation pagination fixture가 page/total 표현.

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
최소 fixture set 존재
fixture client가 endpoint matrix와 연결됨
basic tests에서 live API 호출 없음
10003 multi-vehicle fixture 재현
10001 instrumentation pagination fixture 재현
```
