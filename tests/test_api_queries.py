from datetime import date

from fastapi.testclient import TestClient

from nhtsa_metadata.api.app import _with_crash_family_group_options, create_app
from nhtsa_metadata.config import Settings
from nhtsa_metadata.db.models import CrashTest
from nhtsa_metadata.db.session import (
    create_engine_for_settings,
    create_session_factory,
    ensure_schema,
)
from nhtsa_metadata.services.catalog_builder import CatalogBuilder
from nhtsa_metadata.services.safety_ratings_overlay import (
    ensure_safety_rating_overlay_schema,
    upsert_safety_rating_overlay_rows,
)


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


def test_get_test_detail_excludes_raw_by_default(tmp_settings: Settings) -> None:
    _seed(tmp_settings)
    client = TestClient(create_app(tmp_settings))
    body = client.get("/api/tests/10001").json()
    assert body["found"] is True
    assert "raw_payloads" not in body
    assert body["media_assets"]
    assert body["test_classification"]["test_family"] == "frontal_barrier"


def test_filter_options_are_db_driven(tmp_settings: Settings) -> None:
    _seed(tmp_settings)
    client = TestClient(create_app(tmp_settings))
    body = client.get("/api/filter-options").json()
    assert "vehicle_make" in body
    assert any(option["value"] == "CADILLAC" for option in body["vehicle_make"])


def test_filter_options_add_crash_family_group_facets() -> None:
    options = _with_crash_family_group_options(
        {
            "official_family": [
                {"value": "FRONTAL_FIXED_BARRIER", "test_count": 15},
                {"value": "FRONTAL_OFFSET", "test_count": 1},
                {"value": "FRONTAL_OBLIQUE_RMDB", "test_count": 1},
                {"value": "FRONTAL_OBLIQUE_RMDB_EDGE", "test_count": 1},
                {"value": "SIDE_MDB", "test_count": 4},
                {"value": "SIDE_POLE", "test_count": 3},
                {"value": "REAR_IMPACT", "test_count": 2},
                {"value": "EJM", "test_count": 1},
            ],
            "official_category": [
                {"value": "FMVSS208_56K_FIXED_WALL", "test_count": 1},
                {"value": "FMVSS208_40K_UNBELTED_FIXED_WALL", "test_count": 1},
                {"value": "FRONTAL_FIXED_BARRIER_NCAP_35MPH", "test_count": 7},
                {"value": "FRONTAL_FIXED_BARRIER_RESEARCH_OR_OTHER", "test_count": 2},
                {"value": "FMVSS208_40PCT_OFFSET_ODB", "test_count": 3},
                {"value": "FMVSS208_30DEG_ANGLED_FIXED_WALL", "test_count": 1},
                {"value": "FRONTAL_OFFSET_VTV_15DEG_50PCT_RESEARCH_NON_FMVSS208", "test_count": 1},
                {"value": "SIDE_MDB_NCAP_38_5MPH", "test_count": 2},
                {"value": "SIDE_MDB_FMVSS214", "test_count": 1},
                {"value": "SIDE_MDB_RESEARCH_OR_OTHER", "test_count": 1},
                {"value": "SIDE_POLE_NCAP_75DEG_20MPH", "test_count": 1},
                {"value": "SIDE_POLE_FMVSS214", "test_count": 1},
                {"value": "SIDE_POLE_FMVSS214_MISCoded_VTB", "test_count": 1},
                {"value": "REAR_IMPACT_FMVSS301", "test_count": 1},
                {"value": "REAR_IMPACT_RESEARCH_VTV_OR_ITV", "test_count": 1},
            ],
        }
    )

    assert options["test_family_group"] == [
        {"value": "Frontal", "test_count": 18},
        {"value": "Side", "test_count": 7},
        {"value": "Rear", "test_count": 2},
        {"value": "EJM", "test_count": 1},
    ]
    assert options["official_family_group"] == options["test_family_group"]
    assert options["official_family_by_group"][0]["families"][0] == {
        "value": "FRONTAL_FIXED_BARRIER",
        "label": "정면 고정벽 family",
        "test_count": 15,
    }
    assert options["official_family_detail_by_group"][0]["details"] == [
        {
            "value": "FRONTAL_FIXED_WALL_MODE",
            "label": "정면 고정벽",
            "test_count": 10,
            "families": ["FRONTAL_FIXED_BARRIER"],
            "categories": [
                "FMVSS208_56K_FIXED_WALL",
                "FRONTAL_FIXED_BARRIER_NCAP_35MPH",
                "FRONTAL_FIXED_BARRIER_RESEARCH_OR_OTHER",
            ],
        },
        {
            "value": "FRONTAL_FIXED_WALL_UNBELTED_MODE",
            "label": "정면 고정벽_unbelted",
            "test_count": 1,
            "families": ["FRONTAL_FIXED_BARRIER"],
            "categories": ["FMVSS208_40K_UNBELTED_FIXED_WALL"],
        },
        {
            "value": "FRONTAL_40PCT_OFFSET_ODB_MODE",
            "label": "40% 옵셋(ODB)",
            "test_count": 3,
            "families": ["FRONTAL_FIXED_BARRIER"],
            "categories": ["FMVSS208_40PCT_OFFSET_ODB"],
        },
        {
            "value": "FRONTAL_30DEG_ANGLED_FIXED_WALL_UNBELTED_MODE",
            "label": "30도 경사_unbelted",
            "test_count": 1,
            "families": ["FRONTAL_FIXED_BARRIER"],
            "categories": ["FMVSS208_30DEG_ANGLED_FIXED_WALL"],
        },
        {
            "value": "FRONTAL_OBLIQUE_RMDB_MODE",
            "label": "OBLIQUE/RMDB",
            "test_count": 2,
            "families": ["FRONTAL_OBLIQUE_RMDB", "FRONTAL_OBLIQUE_RMDB_EDGE"],
            "categories": [],
        },
        {
            "value": "FRONTAL_OFFSET_VTV_RESEARCH_MODE",
            "label": "VTV 옵셋 연구",
            "test_count": 1,
            "families": ["FRONTAL_OFFSET"],
            "categories": ["FRONTAL_OFFSET_VTV_15DEG_50PCT_RESEARCH_NON_FMVSS208"],
        },
    ]
    assert options["official_family_detail_by_group"][1]["details"] == [
        {
            "value": "SIDE_MDB_NCAP_38_5MPH_MODE",
            "label": "MDB_NCAP",
            "test_count": 2,
            "families": ["SIDE_MDB"],
            "categories": ["SIDE_MDB_NCAP_38_5MPH"],
        },
        {
            "value": "SIDE_MDB_FMVSS214_MODE",
            "label": "MDB_FMVSS214",
            "test_count": 1,
            "families": ["SIDE_MDB"],
            "categories": ["SIDE_MDB_FMVSS214"],
        },
        {
            "value": "SIDE_MDB_RESEARCH_OR_OTHER_MODE",
            "label": "MDB_research",
            "test_count": 1,
            "families": ["SIDE_MDB"],
            "categories": ["SIDE_MDB_RESEARCH_OR_OTHER"],
        },
        {
            "value": "SIDE_POLE_MODE",
            "label": "POLE",
            "test_count": 3,
            "families": ["SIDE_POLE"],
            "categories": [
                "SIDE_POLE_NCAP_75DEG_20MPH",
                "SIDE_POLE_FMVSS214",
                "SIDE_POLE_FMVSS214_MISCoded_VTB",
            ],
        },
    ]
    assert options["official_family_detail_by_group"][2]["details"] == [
        {
            "value": "REAR_IMPACT_FMVSS301_MODE",
            "label": "후방 FMVSS301",
            "test_count": 1,
            "families": ["REAR_IMPACT"],
            "categories": ["REAR_IMPACT_FMVSS301"],
        },
        {
            "value": "REAR_IMPACT_RESEARCH_VTV_OR_ITV_MODE",
            "label": "후방 Research/VTV/ITV",
            "test_count": 1,
            "families": ["REAR_IMPACT"],
            "categories": ["REAR_IMPACT_RESEARCH_VTV_OR_ITV"],
        },
    ]
    labels = options["official_family_labels"]
    assert labels["FRONTAL_FIXED_WALL_UNBELTED_MODE"] == "정면 고정벽_unbelted"
    assert labels["FRONTAL_40PCT_OFFSET_ODB_MODE"] == "40% 옵셋(ODB)"
    assert labels["FRONTAL_30DEG_ANGLED_FIXED_WALL_UNBELTED_MODE"] == "30도 경사_unbelted"
    assert options["official_family_labels"]["SIDE_MDB_NCAP_38_5MPH_MODE"] == "MDB_NCAP"
    assert options["official_family_labels"]["SIDE_POLE_MODE"] == "POLE"
    assert options["official_family_labels"]["REAR_IMPACT_FMVSS301_MODE"] == "후방 FMVSS301"


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


def test_safety_rating_overlay_summary_and_detail_api(tmp_settings: Settings) -> None:
    engine = create_engine_for_settings(tmp_settings)
    ensure_schema(engine)
    ensure_safety_rating_overlay_schema(engine)
    session_factory = create_session_factory(tmp_settings)
    with session_factory() as session:
        session.add(
            CrashTest(
                test_no=9001,
                test_date=date(2020, 1, 15),
                test_date_parse_status="parsed",
            )
        )
        session.commit()

    upsert_safety_rating_overlay_rows(
        engine,
        [
            {
                "row_key": "9001::1",
                "test_no": 9001,
                "source_vehicle_no": 1,
                "db_make": "FORD",
                "db_model": "EXPLORER",
                "db_model_year": 2020,
                "db_body_style": "UTILITY VEHICLE",
                "db_vin": "1FM5K7D80LGA00001",
                "match_method": "direct",
                "match_confidence": "HIGH_DISAMBIGUATED",
                "query_make": "FORD",
                "query_model": "EXPLORER",
                "variant_count": 2,
                "candidate_rank": 1,
                "candidate_score": 44,
                "candidate_score_reasons": "body:SUV;drive:FWD",
                "rating_vehicle_id": 123,
                "rating_vehicle_description": "2020 Ford Explorer SUV FWD",
                "OverallRating": "5",
                "OverallFrontCrashRating": "5",
                "OverallSideCrashRating": "5",
                "RolloverRating": "4",
                "NHTSAForwardCollisionWarning": "Standard",
            },
            {
                "row_key": "9001::1",
                "test_no": 9001,
                "source_vehicle_no": 1,
                "db_make": "FORD",
                "db_model": "EXPLORER",
                "db_model_year": 2020,
                "db_body_style": "UTILITY VEHICLE",
                "db_vin": "1FM5K7D80LGA00001",
                "match_method": "direct",
                "match_confidence": "HIGH_DISAMBIGUATED",
                "query_make": "FORD",
                "query_model": "EXPLORER",
                "variant_count": 2,
                "candidate_rank": 2,
                "candidate_score": 19,
                "candidate_score_reasons": "body:SUV",
                "rating_vehicle_id": 124,
                "rating_vehicle_description": "2020 Ford Explorer SUV AWD",
                "OverallRating": "5",
                "OverallFrontCrashRating": "5",
                "OverallSideCrashRating": "5",
                "RolloverRating": "4",
            },
        ],
        generated_at="2026-06-29T00:00:00+00:00",
    )

    client = TestClient(create_app(tmp_settings))
    summary = client.get("/api/safety-ratings/summary").json()
    assert summary["available"] is True
    assert summary["source"] == "nhtsa_safety_ratings_overlay"
    assert summary["metrics"]["matched_subject_rows"] == 1
    assert summary["metrics"]["candidate_rows"] == 2
    assert summary["metrics"]["ambiguous_subject_rows"] == 1
    assert summary["official_handling"]["variant_query"] == (
        "modelyear/{year}/make/{make}/model/{model}"
    )
    assert "selected variant" in summary["official_handling"]["selection_rule"].lower()

    match = client.get("/api/safety-ratings/tests/9001").json()
    assert match["available"] is True
    assert match["found"] is True
    assert match["subjects"][0]["selection_status"] == "auto_high_candidate"
    assert match["subjects"][0]["top_candidate"]["rating_vehicle_id"] == 123
    assert len(match["subjects"][0]["candidates"]) == 2

    detail = client.get("/api/tests/9001").json()
    assert detail["safety_rating_match"]["found"] is True
    assert detail["safety_rating_match"]["subjects"][0]["top_candidate"]["OverallRating"] == "5"


def test_metadata_refresh_gui_exposes_safety_rating_overlay_panel(tmp_settings: Settings) -> None:
    ensure_schema(create_engine_for_settings(tmp_settings))
    client = TestClient(create_app(tmp_settings))
    html = client.get("/metadata-refresh").text
    assert "ratingOverlay" in html
    assert "/api/safety-ratings/summary" in html
    assert "NHTSA SafetyRatings" in html
