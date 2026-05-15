from pathlib import Path

from sqlalchemy.orm import Session

from nhtsa_metadata.db.models import CrashTest
from nhtsa_metadata.db.session import (
    create_engine_for_settings,
    create_session_factory,
    ensure_schema,
)
from nhtsa_metadata.services.rule_classifier import classify_database

RULE_FILE = Path(
    "docs/us_fmvss_ncap_crash_test_classification_method_v1_4_1500sample_targeted_rules.json"
)


def test_classifier_separates_alias_from_fallback(tmp_settings) -> None:  # type: ignore[no-untyped-def]
    session = _session(tmp_settings)
    with session as db:
        db.add(
            CrashTest(
                test_no=1,
                test_type="NEW CAR ASSESSMENT TEST",
                test_date_parse_status="parsed",
                contractor_study_title=(
                    "MOVING BARRIER INTO LEFT SIDE OF VEHICLE / DEFORMABLE IMPACTOR"
                ),
                test_configuration="IMPACTOR INTO VEHICLE",
                impact_angle=270,
                closing_speed=62.0,
            )
        )
        db.commit()
        payload = classify_database(
            db,
            rule_file=RULE_FILE,
            source_db="sqlite:///:memory:",
            snapshot_source="test",
        )

    result = payload["results"][0]
    assert result["matched_rule_id"] == "US_NCAP_SIDE_BARRIER_MDB_38_5MPH_3015LB_TITLE_ALIAS"
    assert result["canonical_rule_id"] == "US_NCAP_SIDE_BARRIER_MDB_38_5MPH_3015LB"
    assert result["alias_used"] is True
    assert result["fallback_used"] is False


def test_classifier_keeps_part_581_out_of_fmvss_crashworthiness(tmp_settings) -> None:  # type: ignore[no-untyped-def]
    session = _session(tmp_settings)
    with session as db:
        db.add(
            CrashTest(
                test_no=2,
                test_type="MODIFIED VEHICLE TEST",
                test_date_parse_status="parsed",
                contractor_study_title="PART 581 BUMPER DAMAGEABILITY TEST",
                test_configuration="IMPACTOR INTO VEHICLE",
                impact_angle=0,
                closing_speed=8.0,
            )
        )
        db.commit()
        payload = classify_database(
            db,
            rule_file=RULE_FILE,
            source_db="sqlite:///:memory:",
            snapshot_source="test",
        )

    result = payload["results"][0]
    assert result["matched_rule_id"] == "PART_581_BUMPER_DAMAGEABILITY_LOW_SPEED_IMPACTOR"
    assert result["specificity_level"] == "standard_subtest"
    assert payload["summary"]["known_false_positive_count"] == 0


def test_classifier_routes_research_fmvss_pole_away_from_ncap_side_pole(tmp_settings) -> None:  # type: ignore[no-untyped-def]
    session = _session(tmp_settings)
    with session as db:
        db.add(
            CrashTest(
                test_no=3,
                test_type="RESEARCH",
                test_date_parse_status="parsed",
                contractor_study_title=(
                    "2018 HONDA ACCORD LEFT SIDE FMVSS POLE IMPACT AT 32 KPH"
                ),
                test_configuration="VEHICLE INTO POLE",
                impact_angle=0,
                closing_speed=32.0,
            )
        )
        db.commit()
        payload = classify_database(
            db,
            rule_file=RULE_FILE,
            source_db="sqlite:///:memory:",
            snapshot_source="test",
        )

    result = payload["results"][0]
    assert result["matched_rule_id"] == "NHTSA_RESEARCH_SIDE_POLE_FMVSS_POLE_IMPACT_32KPH"
    assert result["canonical_rule_id"] == "NHTSA_RESEARCH_SIDE_POLE_FMVSS_POLE_IMPACT_32KPH"
    assert payload["summary"]["known_false_positive_count"] == 0


def test_classifier_prioritizes_sled_over_full_vehicle_oblique(tmp_settings) -> None:  # type: ignore[no-untyped-def]
    session = _session(tmp_settings)
    with session as db:
        db.add(
            CrashTest(
                test_no=4,
                test_type="RMDB INTO FRONT 15 DEGREE STATIONARY VEHICLE, OVERLAP=35 PERCENT",
                test_date_parse_status="parsed",
                contractor_study_title="SLED BUCK RESEARCH AND DEVELOPMENT OFFSET TEST",
                test_configuration="SLED WITH VEHICLE BODY",
                impact_angle=15,
                closing_speed=88.0,
            )
        )
        db.commit()
        payload = classify_database(
            db,
            rule_file=RULE_FILE,
            source_db="sqlite:///:memory:",
            snapshot_source="test",
        )

    result = payload["results"][0]
    assert result["matched_rule_id"] == "OCCUPANT_PERFORMANCE_FRONTAL_OBLIQUE_SLED_RESEARCH"
    assert "SLED" in result["canonical_rule_id"]
    assert payload["summary"]["known_false_positive_count"] == 0


def _session(tmp_settings) -> Session:  # type: ignore[no-untyped-def]
    ensure_schema(create_engine_for_settings(tmp_settings))
    return create_session_factory(tmp_settings)()
