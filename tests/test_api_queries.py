from datetime import date

from fastapi.testclient import TestClient

from nhtsa_metadata.api.app import create_app
from nhtsa_metadata.config import Settings
from nhtsa_metadata.db.models import CrashTest
from nhtsa_metadata.db.session import (
    create_engine_for_settings,
    create_session_factory,
    ensure_schema,
)
from nhtsa_metadata.services.catalog_builder import CatalogBuilder


def _seed(settings: Settings) -> None:
    ensure_schema(create_engine_for_settings(settings))
    session_factory = create_session_factory(settings)
    with session_factory() as session:
        CatalogBuilder(session).collect_tests([10001, 10003])


def test_list_tests_and_filters(tmp_settings: Settings) -> None:
    _seed(tmp_settings)
    client = TestClient(create_app(tmp_settings))
    response = client.get("/api/tests", params={"vehicle_make": "CHEVROLET"})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["items"][0]["test_no"] == 10003
    response = client.get(
        "/api/tests",
        params={"wheelbase_min": 2900, "has_load_cell_barrier": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["items"][0]["test_no"] == 10001
    assert body["items"][0]["vehicle_length_min"] == 5180.0
    assert body["items"][0]["has_load_cell_barrier"] is True


def test_get_test_detail_excludes_raw_by_default(tmp_settings: Settings) -> None:
    _seed(tmp_settings)
    client = TestClient(create_app(tmp_settings))
    body = client.get("/api/tests/10001").json()
    assert body["found"] is True
    assert "raw_payloads" not in body
    assert body["media_assets"]
    assert body["test_classification"]["test_family"] == "frontal_barrier"
    assert body["vehicles"][0]["body_type"] == "UTILITY VEHICLE"
    assert body["vehicles"][0]["wheelbase"] == 2955.0


def test_filter_options_are_db_driven(tmp_settings: Settings) -> None:
    _seed(tmp_settings)
    client = TestClient(create_app(tmp_settings))
    body = client.get("/api/filter-options").json()
    assert "vehicle_make" in body
    assert any(option["value"] == "CADILLAC" for option in body["vehicle_make"])


def test_coverage_fields_and_collection_runs(tmp_settings: Settings) -> None:
    _seed(tmp_settings)
    client = TestClient(create_app(tmp_settings))
    coverage = client.get("/api/coverage/fields").json()
    runs = client.get("/api/collection-runs").json()
    assert coverage["count"] > 0
    assert runs["count"] >= 1


def test_get_test_detail_hides_out_of_scope_stale_canonical_row(
    tmp_settings: Settings,
) -> None:
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    with session_factory() as session:
        session.add(
            CrashTest(
                test_no=1,
                test_date=date(2010, 12, 31),
                test_date_parse_status="parsed",
            )
        )
        session.commit()
    client = TestClient(create_app(tmp_settings))
    body = client.get("/api/tests/1").json()
    assert body == {
        "test_no": 1,
        "found": False,
        "reason": "out_of_scope",
        "min_test_date": "2011-01-01",
    }
