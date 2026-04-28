# Phase 2 — DB Foundation 작업지시서

## 목표

SQLAlchemy/Alembic 기반으로 raw/provenance, canonical core, filter/read-model schema를 구축한다. Parser와 ingestion full logic은 Phase 4/5에서 구현하되, 이 phase에서는 migration, model import, 기본 repository test가 통과해야 한다.

## 설계 원칙

1. FK는 내부 integer PK를 사용한다.
2. 외부 natural key(`test_no`, `vehicle_no`, `curve_no`)는 unique/index로 관리한다.
3. raw payload는 immutable store다.
4. canonical row는 lineage columns를 가진다.
5. read model은 canonical에서 rebuild 가능한 파생물이다.
6. SQLite로 시작하지만 PostgreSQL 이전을 방해하지 않는다.

## 생성/수정 파일

```text
alembic.ini
alembic/env.py
alembic/versions/0001_initial_schema.py
src/nhtsa_metadata/db/base.py
src/nhtsa_metadata/db/models.py
src/nhtsa_metadata/db/session.py
src/nhtsa_metadata/db/migrations.py
src/nhtsa_metadata/services/db_health.py
docs/db_schema.md
docs/phase_reports/phase_2_db_foundation.md
tests/test_db_migrations.py
tests/test_db_models.py
```

## 공통 column 정책

### Timestamp

모든 주요 table:

```text
created_at DATETIME NOT NULL
updated_at DATETIME NULL
```

### JSON

SQLAlchemy `JSON` 사용. SQLite에서는 text storage가 되더라도 model API는 dict/list로 동작해야 한다.

### Hash

```text
payload_hash         SHA-256 hex, length 64
source_row_hash      SHA-256 hex, length 64
canonical_url_hash   SHA-256 hex, length 64
```

### Canonical lineage mixin

canonical table에는 다음 columns를 둔다.

```text
source_payload_id       FK source_payloads.id NULL
source_endpoint_name    TEXT NULL
source_section_name     TEXT NULL
source_row_path         TEXT NULL
source_row_hash         TEXT NULL
raw_row_json            JSON NULL
extra_json              JSON NULL
```

## Raw / Provenance layer

### `collection_runs`

목적: 수집 실행 단위.

핵심 columns:

```text
id PK
run_uuid TEXT UNIQUE NOT NULL
run_type TEXT NOT NULL                 # discover, collect, collect_test, rebuild, live_validation
mode TEXT NOT NULL                     # fixture, live, rebuild
status TEXT NOT NULL                   # running, succeeded, failed, partial, dry_run
input_manifest_path TEXT NULL
input_manifest_hash TEXT NULL
input_range_json JSON NULL
database_url_sanitized TEXT NULL
endpoint_set TEXT NULL
include_detail_endpoints BOOLEAN NOT NULL DEFAULT 0
paginate_instrumentation BOOLEAN NOT NULL DEFAULT 0
dry_run BOOLEAN NOT NULL DEFAULT 0
allow_live BOOLEAN NOT NULL DEFAULT 0
retry_count INTEGER NOT NULL DEFAULT 0
timeout_seconds NUMERIC NULL
rate_limit_delay_seconds NUMERIC NULL
success_count INTEGER NOT NULL DEFAULT 0
failure_count INTEGER NOT NULL DEFAULT 0
skipped_count INTEGER NOT NULL DEFAULT 0
started_at DATETIME NOT NULL
ended_at DATETIME NULL
software_version TEXT NULL
extra_json JSON NULL
created_at DATETIME NOT NULL
updated_at DATETIME NULL
```

Indexes:

```text
idx_collection_runs_started_at
idx_collection_runs_status
```

### `collection_run_items`

목적: test_no별 수집 상태.

```text
id PK
run_id FK collection_runs.id NOT NULL
test_no INTEGER NOT NULL
status TEXT NOT NULL                   # pending, running, succeeded, failed, skipped, partial
attempt_count INTEGER NOT NULL DEFAULT 0
started_at DATETIME NULL
ended_at DATETIME NULL
last_error_type TEXT NULL
last_error_message TEXT NULL
endpoints_attempted_json JSON NULL
endpoints_succeeded_json JSON NULL
endpoints_failed_json JSON NULL
endpoint_statuses_json JSON NULL
extra_json JSON NULL
created_at DATETIME NOT NULL
updated_at DATETIME NULL
```

Unique:

```text
unique(run_id, test_no)
```

### `source_endpoints`

목적: endpoint template catalog.

```text
id PK
name TEXT UNIQUE NOT NULL
endpoint_group TEXT NOT NULL           # discovery, core, core_optional, detail, assets
method TEXT NOT NULL DEFAULT 'GET'
path_template TEXT NOT NULL
is_paginated BOOLEAN NOT NULL DEFAULT 0
default_count INTEGER NULL
requires_test_no BOOLEAN NOT NULL DEFAULT 1
requires_vehicle_no BOOLEAN NOT NULL DEFAULT 0
requires_occupant_location BOOLEAN NOT NULL DEFAULT 0
requires_curve_no BOOLEAN NOT NULL DEFAULT 0
allow_empty BOOLEAN NOT NULL DEFAULT 1
required_for_baseline BOOLEAN NOT NULL DEFAULT 0
parser_name TEXT NOT NULL
enabled BOOLEAN NOT NULL DEFAULT 1
notes TEXT NULL
extra_json JSON NULL
created_at DATETIME NOT NULL
updated_at DATETIME NULL
```

Seed는 migration 또는 idempotent bootstrap에서 넣는다. 권장: migration seed.

### `source_payloads`

목적: immutable raw payload store.

```text
id PK
endpoint_id FK source_endpoints.id NULL
endpoint_name TEXT NOT NULL
source TEXT NOT NULL DEFAULT 'nhtsa_crash'
test_no INTEGER NULL
vehicle_no INTEGER NULL
occupant_location_raw TEXT NULL
curve_no INTEGER NULL
page_number INTEGER NULL
request_url TEXT NOT NULL
canonical_url_hash TEXT NOT NULL
http_status INTEGER NULL
api_status INTEGER NULL
api_message TEXT NULL
api_error TEXT NULL
pagination_json JSON NULL
count_returned INTEGER NULL
total_available INTEGER NULL
payload_hash TEXT NOT NULL
payload_json JSON NOT NULL
fetched_at DATETIME NOT NULL
created_at DATETIME NOT NULL
updated_at DATETIME NULL
```

Unique:

```text
unique(endpoint_name, canonical_url_hash, payload_hash)
```

Indexes:

```text
idx_source_payloads_test_no
idx_source_payloads_endpoint_test
idx_source_payloads_payload_hash
idx_source_payloads_fetched_at
```

### `source_payload_observations`

목적: 동일 payload의 반복 관측 이력.

```text
id PK
source_payload_id FK source_payloads.id NOT NULL
run_id FK collection_runs.id NULL
run_item_id FK collection_run_items.id NULL
observed_at DATETIME NOT NULL
http_status INTEGER NULL
elapsed_ms INTEGER NULL
response_size_bytes INTEGER NULL
request_headers_json JSON NULL
response_headers_json JSON NULL
extra_json JSON NULL
created_at DATETIME NOT NULL
```

### `source_payload_sections`

```text
id PK
source_payload_id FK source_payloads.id NOT NULL
section_name TEXT NOT NULL
json_path TEXT NOT NULL
row_count INTEGER NOT NULL DEFAULT 0
section_hash TEXT NULL
sample_json JSON NULL
created_at DATETIME NOT NULL
updated_at DATETIME NULL
```

Unique:

```text
unique(source_payload_id, section_name, json_path)
```

### `source_field_catalog`

```text
id PK
endpoint_name TEXT NOT NULL
section_name TEXT NULL
field_path TEXT NOT NULL
observed_type TEXT NOT NULL
first_seen_at DATETIME NOT NULL
last_seen_at DATETIME NOT NULL
seen_count INTEGER NOT NULL DEFAULT 0
non_null_count INTEGER NOT NULL DEFAULT 0
mapping_status TEXT NOT NULL DEFAULT 'unmapped'
mapped_table TEXT NULL
mapped_column TEXT NULL
example_values_json JSON NULL
created_at DATETIME NOT NULL
updated_at DATETIME NULL
```

Unique:

```text
unique(endpoint_name, section_name, field_path)
```

### `source_conflicts`

```text
id PK
test_no INTEGER NOT NULL
field_semantic_key TEXT NOT NULL
canonical_table TEXT NULL
canonical_column TEXT NULL
endpoint_a TEXT NOT NULL
source_payload_id_a FK source_payloads.id NULL
value_a_json JSON NULL
endpoint_b TEXT NOT NULL
source_payload_id_b FK source_payloads.id NULL
value_b_json JSON NULL
resolution_status TEXT NOT NULL DEFAULT 'unresolved'
resolved_value_json JSON NULL
notes TEXT NULL
created_at DATETIME NOT NULL
updated_at DATETIME NULL
```

### `canonical_row_sources`

```text
id PK
canonical_table TEXT NOT NULL
canonical_id INTEGER NOT NULL
source_payload_id FK source_payloads.id NOT NULL
source_endpoint_name TEXT NOT NULL
source_section_name TEXT NULL
source_row_path TEXT NULL
source_row_hash TEXT NULL
created_at DATETIME NOT NULL
```

Indexes:

```text
idx_canonical_row_sources_table_id
idx_canonical_row_sources_payload
```

## Canonical core layer

### `tests`

핵심 columns:

```text
id PK
test_no INTEGER UNIQUE NOT NULL
test_reference_no TEXT NULL
test_type TEXT NULL
test_title TEXT NULL
contractor_study_title TEXT NULL
test_performer TEXT NULL
contract_number TEXT NULL
test_objective TEXT NULL
test_configuration TEXT NULL
test_configuration_key TEXT NULL
impact_angle_raw TEXT NULL
impact_angle NUMERIC NULL
offset_distance_raw TEXT NULL
offset_distance NUMERIC NULL
closing_speed_raw TEXT NULL
closing_speed NUMERIC NULL
closing_speed_unit_raw TEXT NULL
closing_speed_parse_status TEXT NOT NULL DEFAULT 'missing'
measured_unit_raw TEXT NULL
total_curve_count_raw TEXT NULL
total_curve_count INTEGER NULL
test_date_raw TEXT NULL
test_date DATE NULL
test_year INTEGER NULL
test_month INTEGER NULL
test_day INTEGER NULL
test_date_parse_status TEXT NOT NULL DEFAULT 'missing'
test_date_source_endpoint TEXT NULL
track_condition TEXT NULL
<lineage columns>
created_at DATETIME NOT NULL
updated_at DATETIME NULL
```

Indexes:

```text
idx_tests_test_type
idx_tests_test_configuration
idx_tests_test_date
idx_tests_closing_speed
```

### `vehicles`

```text
id PK
test_id FK tests.id NOT NULL
source_vehicle_no INTEGER NOT NULL
make TEXT NULL
model TEXT NULL
model_year INTEGER NULL
vin TEXT NULL
body_type TEXT NULL
engine_type TEXT NULL
transmission TEXT NULL
drive_type TEXT NULL
vehicle_test_weight_raw TEXT NULL
vehicle_test_weight NUMERIC NULL
vehicle_length_raw TEXT NULL
vehicle_length NUMERIC NULL
vehicle_width_raw TEXT NULL
vehicle_width NUMERIC NULL
vehicle_speed_raw TEXT NULL
vehicle_speed NUMERIC NULL
vax_crush_distance_raw TEXT NULL
vax_crush_distance NUMERIC NULL
<lineage columns>
```

Unique: `unique(test_id, source_vehicle_no)`

Indexes: `idx_vehicles_make_model_year`, `idx_vehicles_test_id`

### `barriers`

```text
id PK
test_id FK tests.id NOT NULL
rigidity TEXT NULL
shape TEXT NULL
barrier_type TEXT NULL
angle_raw TEXT NULL
angle NUMERIC NULL
diameter_raw TEXT NULL
diameter NUMERIC NULL
barrier_commentary TEXT NULL
source_barrier_no TEXT NULL
<lineage columns>
```

Unique: `unique(test_id, source_row_hash)`

### `test_participants`

```text
id PK
test_id FK tests.id NOT NULL
participant_kind TEXT NOT NULL      # subject_vehicle, impactor_vehicle, barrier, sled, other, unknown
vehicle_id FK vehicles.id NULL
barrier_id FK barriers.id NULL
source_vehicle_no INTEGER NULL
display_name TEXT NULL
classification_reason TEXT NULL
<lineage columns>
```

Service-level idempotency로 `(test_id, participant_kind, vehicle_id, barrier_id, source_vehicle_no)` 중복을 막는다.

### `occupants`

```text
id PK
test_id FK tests.id NOT NULL
vehicle_id FK vehicles.id NULL
source_vehicle_no INTEGER NULL
occupant_location_raw TEXT NOT NULL
occupant_location_normalized TEXT NULL
seat_position TEXT NULL
occupant_type TEXT NULL
dummy_type TEXT NULL
sex TEXT NULL
size_percentile TEXT NULL
age_raw TEXT NULL
age NUMERIC NULL
height_raw TEXT NULL
height NUMERIC NULL
weight_raw TEXT NULL
weight NUMERIC NULL
contact_points_json JSON NULL
<lineage columns>
```

Unique: `unique(test_id, source_vehicle_no, occupant_location_raw, source_row_hash)`

### `restraints`

```text
id PK
test_id FK tests.id NOT NULL
vehicle_id FK vehicles.id NULL
occupant_id FK occupants.id NULL
source_vehicle_no INTEGER NULL
occupant_location_raw TEXT NULL
restraint_type TEXT NULL
restraint_type_raw TEXT NULL
restraint_location TEXT NULL
mounting_location TEXT NULL
manufacturer TEXT NULL
model TEXT NULL
deployment_status TEXT NULL
deployment_raw TEXT NULL
pretensioner_deployment TEXT NULL
airbag_stage TEXT NULL
commentary TEXT NULL
<lineage columns>
```

Unique: `unique(test_id, source_vehicle_no, occupant_location_raw, restraint_type_raw, deployment_raw, source_row_hash)`

### `instrumentation_channels`

```text
id PK
test_id FK tests.id NOT NULL
vehicle_id FK vehicles.id NULL
occupant_id FK occupants.id NULL
curve_no INTEGER NOT NULL
channel_no TEXT NULL
sensor_type TEXT NULL
sensor_location TEXT NULL
sensor_attachment TEXT NULL
sensor_axis TEXT NULL
axis_direction_raw TEXT NULL
unit_raw TEXT NULL
engineering_unit TEXT NULL
data_status TEXT NULL
channel_status TEXT NULL
filter_class TEXT NULL
sample_rate_raw TEXT NULL
sample_rate NUMERIC NULL
time_increment_raw TEXT NULL
time_increment NUMERIC NULL
first_point_raw TEXT NULL
first_point NUMERIC NULL
last_point_raw TEXT NULL
last_point NUMERIC NULL
commentary TEXT NULL
<lineage columns>
```

Unique: `unique(test_id, curve_no)`

Indexes: sensor_type, sensor_location, sensor_axis, engineering_unit.

### `instrumentation_channel_details`

```text
id PK
instrumentation_channel_id FK instrumentation_channels.id NULL
test_id FK tests.id NOT NULL
curve_no INTEGER NOT NULL
detail_key TEXT NOT NULL
detail_value_raw TEXT NULL
detail_value_numeric NUMERIC NULL
unit_raw TEXT NULL
parse_status TEXT NOT NULL DEFAULT 'missing'
<lineage columns>
```

### `injury_metrics`

Long-form metric table.

```text
id PK
test_id FK tests.id NOT NULL
vehicle_id FK vehicles.id NULL
occupant_id FK occupants.id NULL
metric_code TEXT NOT NULL
metric_name TEXT NULL
metric_family TEXT NULL
metric_context TEXT NULL
raw_value TEXT NULL
numeric_value NUMERIC NULL
unit_raw TEXT NULL
parse_status TEXT NOT NULL DEFAULT 'missing'
<lineage columns>
```

Unique: `unique(test_id, occupant_id, metric_code, metric_context, source_row_hash)`

### `deformation_measurements`

```text
id PK
test_id FK tests.id NOT NULL
vehicle_id FK vehicles.id NULL
measurement_family TEXT NOT NULL       # DPD, AX, BX, DAMDST, CRHDST, PDOF, VDI, other
measurement_code TEXT NOT NULL
measurement_index INTEGER NULL
raw_value TEXT NULL
numeric_value NUMERIC NULL
unit_raw TEXT NULL
parse_status TEXT NOT NULL DEFAULT 'missing'
<lineage columns>
```

Unique: `unique(test_id, vehicle_id, measurement_family, measurement_code, measurement_index)`

### `intrusion_measurements`

```text
id PK
test_id FK tests.id NOT NULL
vehicle_id FK vehicles.id NULL
source_vehicle_no INTEGER NULL
location_code_raw TEXT NULL
measurement_code_raw TEXT NOT NULL
measurement_family TEXT NULL
raw_value TEXT NULL
numeric_value NUMERIC NULL
unit_raw TEXT NULL
parse_status TEXT NOT NULL DEFAULT 'missing'
<lineage columns>
```

### `media_assets`

```text
id PK
test_id FK tests.id NOT NULL
asset_kind TEXT NOT NULL
source_url TEXT NOT NULL
canonical_url_hash TEXT NOT NULL
file_ext TEXT NULL
suggested_filename TEXT NULL
content_type TEXT NULL
size_bytes INTEGER NULL
title TEXT NULL
description TEXT NULL
<lineage columns>
```

Unique: `unique(test_id, asset_kind, canonical_url_hash)`

### `code_values`

```text
id PK
code_set TEXT NOT NULL
code_value TEXT NOT NULL
normalized_value TEXT NULL
description TEXT NULL
first_seen_test_id FK tests.id NULL
seen_count INTEGER NOT NULL DEFAULT 0
extra_json JSON NULL
created_at DATETIME NOT NULL
updated_at DATETIME NULL
```

Unique: `unique(code_set, code_value)`

## Read model layer

### `test_filter_summary`

One row per test.

```text
id PK
test_id FK tests.id UNIQUE NOT NULL
test_no INTEGER UNIQUE NOT NULL
test_type TEXT NULL
test_configuration TEXT NULL
test_date DATE NULL
model_year_min INTEGER NULL
model_year_max INTEGER NULL
vehicle_makes_json JSON NULL
vehicle_models_json JSON NULL
participant_kinds_json JSON NULL
barrier_rigidities_json JSON NULL
barrier_shapes_json JSON NULL
occupant_locations_json JSON NULL
dummy_types_json JSON NULL
restraint_types_json JSON NULL
restraint_deployments_json JSON NULL
sensor_types_json JSON NULL
sensor_locations_json JSON NULL
sensor_axes_json JSON NULL
sensor_units_json JSON NULL
injury_metric_codes_json JSON NULL
deformation_codes_json JSON NULL
asset_kinds_json JSON NULL
has_photo BOOLEAN NOT NULL DEFAULT 0
has_video BOOLEAN NOT NULL DEFAULT 0
has_report BOOLEAN NOT NULL DEFAULT 0
has_data_package BOOLEAN NOT NULL DEFAULT 0
has_uds_or_tdms_package BOOLEAN NOT NULL DEFAULT 0
asset_counts_json JSON NULL
summary_json JSON NULL
rebuilt_at DATETIME NOT NULL
created_at DATETIME NOT NULL
updated_at DATETIME NULL
```

### `test_facets`

```text
id PK
test_id FK tests.id NOT NULL
test_no INTEGER NOT NULL
facet_name TEXT NOT NULL
facet_value TEXT NOT NULL
facet_value_normalized TEXT NULL
facet_scope TEXT NULL
source_table TEXT NULL
source_id INTEGER NULL
created_at DATETIME NOT NULL
```

Unique: `unique(test_id, facet_name, facet_value, facet_scope, source_table, source_id)`

Indexes: `idx_test_facets_name_value`, `idx_test_facets_test_name`.

### `asset_summary`

```text
id PK
test_id FK tests.id UNIQUE NOT NULL
test_no INTEGER UNIQUE NOT NULL
photo_count INTEGER NOT NULL DEFAULT 0
video_count INTEGER NOT NULL DEFAULT 0
report_count INTEGER NOT NULL DEFAULT 0
document_count INTEGER NOT NULL DEFAULT 0
data_package_count INTEGER NOT NULL DEFAULT 0
asset_kinds_json JSON NULL
rebuilt_at DATETIME NOT NULL
created_at DATETIME NOT NULL
updated_at DATETIME NULL
```

### `field_coverage_snapshots`

```text
id PK
run_id FK collection_runs.id NULL
snapshot_at DATETIME NOT NULL
total_fields INTEGER NOT NULL
mapped_fields INTEGER NOT NULL
mapped_to_extra_json_fields INTEGER NOT NULL
unmapped_fields INTEGER NOT NULL
ignored_fields INTEGER NOT NULL
conflict_fields INTEGER NOT NULL
by_endpoint_json JSON NULL
created_at DATETIME NOT NULL
```

## SQLAlchemy/Alembic 지침

- SQLAlchemy 2.0 style 사용.
- `Base`는 `src/nhtsa_metadata/db/base.py`.
- model은 우선 `src/nhtsa_metadata/db/models.py`에 둔다.
- `session.py`는 engine/session factory/context manager 제공.
- SQLite file URL parent directory 자동 생성.
- `alembic/env.py`는 `Base.metadata`를 target metadata로 사용.
- `0001_initial_schema.py`는 upgrade/downgrade 모두 구현.
- downgrade는 FK 역순으로 drop.

## `docs/db_schema.md`

다음 포함:

```text
table group 개요
각 table 목적
핵심 column
unique key
index
raw/parsed value policy
lineage policy
rebuild 가능성
```

## 테스트

`tests/test_db_migrations.py`:

- tmp SQLite DB에 Alembic upgrade head.
- 필수 table 목록 존재.
- Alembic downgrade base 가능.

`tests/test_db_models.py`:

- `source_endpoints` seed 또는 insert 가능.
- `tests` row insert 가능.
- `vehicles`가 `tests.id` FK 연결.
- unique constraint 동작.
- JSON column dict 저장/조회 가능.
- canonical model이 lineage columns 보유.

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
Alembic upgrade/downgrade 성공
docs/db_schema.md와 실제 table 목록 일치
canonical tables가 lineage columns 보유
source_payloads payload hash unique 정책 구현
read model tables 존재
```
