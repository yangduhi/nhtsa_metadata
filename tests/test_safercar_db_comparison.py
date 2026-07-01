from __future__ import annotations

import csv
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

from sqlalchemy import create_engine

from nhtsa_metadata.services.safety_ratings_overlay import upsert_safety_rating_overlay_rows

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "compare_safercar_csv_to_db.py"
spec = importlib.util.spec_from_file_location("safercar_db_compare", SCRIPT_PATH)
assert spec is not None and spec.loader is not None
safercar_db_compare = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = safercar_db_compare
spec.loader.exec_module(safercar_db_compare)


def _write_safercar_csv(path: Path, *, rollover_stars: str = "4") -> None:
    rows = [
        {
            "MODEL_YR": "2019",
            "MAKE": "TOYOTA",
            "MODEL": "RAV4",
            "BODY_STYLE": "SUV",
            "VEHICLE_TYPE": "MPV",
            "DRIVE_TRAIN": "FWD",
            "PRODUCTION_RELEASE": "1",
            "OVERALL_STARS": "5",
            "OVERALL_FRNT_STARS": "4",
            "OVERALL_SIDE_STARS": "5",
            "STATIC_STABI_FACTOR": "1.20",
            "TIP": "No Tip",
            "ROLLOVER_POSSIBILITY": "0.160",
            "ROLLOVER_STARS": "4",
            "ROLL_SAFETY_CONCERN": "",
            "ROLL_FOOT_NOTES": "fwd note",
            "FRNT_DRIV_STARS": "4",
            "FRNT_PASS_STARS": "4",
            "SIDE_DRIV_STARS": "4",
            "SIDE_PASS_STARS": "4",
            "SIDE_BARRIER_STAR": "4",
            "COMB_FRNT_STAR": "4",
            "COMB_REAR_STAR": "4",
            "SIDE_POLE_STARS": "4",
            "NHTSA_ESC": "No",
            "NHTSA_FRNT_COLLISION_WARNING": "No",
            "NHTSA_FCW_EVALUATION": "Does Not Meet Performance Criteria",
            "NHTSA_LANE_DEPARTURE_WARNING": "Optional",
            "NHTSA_LDW_EVALUATION": "Test Pending",
            "NHTSA_BACKUP_CAMERA": "Optional",
            "FRNT_TEST_NO": "81234",
            "FRNT_VIN": "JTMDFREV0KJ000000",
            "SIDE_TEST_NO": "81235",
            "POLE_TEST_NO": "81236",
            "HIC15_DRIV": "333",
            "CHEST_DEFL_DRIV": "24.1",
            "POLE_HIC_36_DRIV": "155.0",
        },
        {
            "MODEL_YR": "2019",
            "MAKE": "TOYOTA",
            "MODEL": "RAV4",
            "BODY_STYLE": "SUV",
            "VEHICLE_TYPE": "MPV",
            "DRIVE_TRAIN": "AWD",
            "PRODUCTION_RELEASE": "1",
            "OVERALL_STARS": "5",
            "OVERALL_FRNT_STARS": "4",
            "OVERALL_SIDE_STARS": "5",
            "STATIC_STABI_FACTOR": "1.27",
            "TIP": "No Tip",
            "ROLLOVER_POSSIBILITY": "0.155",
            "ROLLOVER_STARS": rollover_stars,
            "ROLL_SAFETY_CONCERN": "None",
            "ROLL_FOOT_NOTES": "awd note",
            "FRNT_DRIV_STARS": "5",
            "FRNT_PASS_STARS": "4",
            "SIDE_DRIV_STARS": "5",
            "SIDE_PASS_STARS": "5",
            "SIDE_BARRIER_STAR": "5",
            "COMB_FRNT_STAR": "5",
            "COMB_REAR_STAR": "4",
            "SIDE_POLE_STARS": "5",
            "NHTSA_ESC": "Standard",
            "NHTSA_FRNT_COLLISION_WARNING": "Optional",
            "NHTSA_FCW_EVALUATION": "Meets Performance Criteria",
            "NHTSA_LANE_DEPARTURE_WARNING": "No",
            "NHTSA_LDW_EVALUATION": "Test Pending",
            "NHTSA_BACKUP_CAMERA": "Standard",
            "FRNT_TEST_NO": "91234",
            "FRNT_VIN": "JTMDFREV0KJ000001",
            "SIDE_TEST_NO": "91235",
            "POLE_TEST_NO": "91236",
            "HIC15_DRIV": "277",
            "CHEST_DEFL_DRIV": "22.4",
            "POLE_HIC_36_DRIV": "144.0",
        },
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        fieldnames = list(dict.fromkeys(key for row in rows for key in row))
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _seed_overlay(
    db_path: Path,
    *,
    rollover_rating: str = "4",
    rating_vehicle_description: str = "2019 Toyota RAV4 SUV AWD",
) -> None:
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", future=True)
    upsert_safety_rating_overlay_rows(
        engine,
        [
            {
                "row_key": "10704::1",
                "test_no": 10704,
                "source_vehicle_no": 1,
                "db_make": "TOYOTA",
                "db_model": "RAV4",
                "db_model_year": 2019,
                "db_body_type": "SUV",
                "db_body_style": "SUV",
                "match_method": "fixture",
                "match_confidence": "HIGH_DISAMBIGUATED",
                "query_make": "TOYOTA",
                "query_model": "RAV4",
                "variant_count": 2,
                "candidate_rank": 1,
                "candidate_score": 50,
                "rating_vehicle_id": 14082,
                "rating_vehicle_description": rating_vehicle_description,
                "OverallRating": "5",
                "OverallFrontCrashRating": "4",
                "OverallSideCrashRating": "5",
                "FrontCrashDriversideRating": "5",
                "FrontCrashPassengersideRating": "4",
                "SideCrashDriversideRating": "5",
                "SideCrashPassengersideRating": "5",
                "SidePoleCrashRating": "5",
                "NHTSAElectronicStabilityControl": "Standard",
                "NHTSAForwardCollisionWarning": "Optional",
                "NHTSALaneDepartureWarning": "No",
                "RolloverRating": rollover_rating,
                "RolloverPossibility": "0.155",
                "dynamicTipResult": "No Tip",
            }
        ],
        generated_at="2026-06-30T00:00:00+00:00",
    )


def test_compare_safercar_csv_to_db_writes_adoption_ready_artifacts(tmp_path: Path) -> None:
    db_path = tmp_path / "metadata.sqlite"
    csv_path = tmp_path / "Safercar_data.csv"
    outdir = tmp_path / "audit"
    _seed_overlay(db_path)
    _write_safercar_csv(csv_path)

    summary = safercar_db_compare.compare_safercar_to_db(
        db_path=db_path,
        safercar_csv=csv_path,
        outdir=outdir,
    )

    assert summary["candidate_rows"] == 1
    assert summary["matched_candidate_rows"] == 1
    assert summary["adoption_status_counts"] == {"READY_OFFICIAL_ENRICHMENT": 1}
    assert summary["conflict_rows"] == 0

    adoption_rows = list(csv.DictReader((outdir / "adoption_candidates.csv").open()))
    assert adoption_rows[0]["static_stability_factor_csv"] == "1.27"
    assert adoption_rows[0]["selected_variant_reasons"] == "drive:AWD;body:SUV"
    assert adoption_rows[0]["adoptable_fields"] == (
        "static_stability_factor;safercar_dynamic_tip_result;"
        "safercar_rollover_possibility;rollover_stars;"
        "roll_safety_concern;roll_foot_notes"
    )

    field_rows = list(csv.DictReader((outdir / "field_coverage.csv").open()))
    rollover_ssf = next(row for row in field_rows if row["safercar_field"] == "STATIC_STABI_FACTOR")
    assert rollover_ssf["recommended_action"] == "ADOPT_TO_OFFICIAL_ROLLOVER_OVERLAY"

    report = json.loads((outdir / "summary.json").read_text(encoding="utf-8"))
    assert report["outputs"]["adoption_candidates_csv"].endswith("adoption_candidates.csv")


def test_compare_safercar_csv_to_db_flags_rating_conflicts(tmp_path: Path) -> None:
    db_path = tmp_path / "metadata.sqlite"
    csv_path = tmp_path / "Safercar_data.csv"
    outdir = tmp_path / "audit"
    _seed_overlay(db_path, rollover_rating="3")
    _write_safercar_csv(csv_path, rollover_stars="4")

    summary = safercar_db_compare.compare_safercar_to_db(
        db_path=db_path,
        safercar_csv=csv_path,
        outdir=outdir,
    )

    assert summary["adoption_status_counts"] == {"REVIEW_CONFLICT": 1}
    assert summary["conflict_rows"] == 1
    conflict_rows = list(csv.DictReader((outdir / "conflicts.csv").open()))
    assert conflict_rows[0]["field_pair"] == "rollover_rating_vs_ROLLOVER_STARS"
    assert conflict_rows[0]["db_value"] == "3"
    assert conflict_rows[0]["safercar_value"] == "4"


def test_compare_safercar_csv_to_db_prefers_later_release_variant(tmp_path: Path) -> None:
    db_path = tmp_path / "metadata.sqlite"
    csv_path = tmp_path / "Safercar_data.csv"
    outdir = tmp_path / "audit"
    _seed_overlay(
        db_path,
        rating_vehicle_description="2019 Toyota RAV4 SUV AWD Later Release",
    )
    csv_path.write_text(
        "MODEL_YR,MAKE,MODEL,BODY_STYLE,VEHICLE_TYPE,DRIVE_TRAIN,PRODUCTION_RELEASE,"
        "OVERALL_STARS,OVERALL_FRNT_STARS,OVERALL_SIDE_STARS,STATIC_STABI_FACTOR,TIP,"
        "ROLLOVER_POSSIBILITY,ROLLOVER_STARS,ROLL_SAFETY_CONCERN,ROLL_FOOT_NOTES\n"
        "2019,TOYOTA,RAV4,SUV,MPV,AWD,1,5,4,5,1.20,No Tip,0.160,4,,early note\n"
        "2019,TOYOTA,RAV4,SUV,MPV,AWD,2,5,4,5,1.27,No Tip,0.155,4,,later note\n",
        encoding="utf-8",
    )

    summary = safercar_db_compare.compare_safercar_to_db(
        db_path=db_path,
        safercar_csv=csv_path,
        outdir=outdir,
    )

    assert summary["conflict_rows"] == 0
    adoption_rows = list(csv.DictReader((outdir / "adoption_candidates.csv").open()))
    assert adoption_rows[0]["static_stability_factor_csv"] == "1.27"
    assert adoption_rows[0]["selected_variant_reasons"] == "drive:AWD;release:LATER;body:SUV"


def test_apply_safercar_authority_overwrites_db_rating_fields(tmp_path: Path) -> None:
    db_path = tmp_path / "metadata.sqlite"
    csv_path = tmp_path / "Safercar_data.csv"
    outdir = tmp_path / "authority"
    _seed_overlay(db_path, rollover_rating="3")
    con = sqlite3.connect(db_path)
    con.execute(
        """
        update nhtsa_rating_match_candidates
        set front_crash_driver_side_rating='3',
            side_pole_crash_rating='4',
            nhtsa_electronic_stability_control='No',
            nhtsa_forward_collision_warning='No',
            nhtsa_lane_departure_warning='Optional'
        where row_key='10704::1'
        """
    )
    con.commit()
    _write_safercar_csv(csv_path, rollover_stars="4")

    summary = safercar_db_compare.apply_safercar_authority_to_db(
        db_path=db_path,
        safercar_csv=csv_path,
        outdir=outdir,
        generated_at="2026-06-30T12:00:00+00:00",
    )

    assert summary["updated_rows"] == 1
    assert summary["overridden_value_count"] >= 6

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    row = con.execute(
        "select * from nhtsa_rating_match_candidates where row_key='10704::1'"
    ).fetchone()
    assert row["rollover_rating"] == "4"
    assert row["front_crash_driver_side_rating"] == "5"
    assert row["side_pole_crash_rating"] == "5"
    assert row["nhtsa_electronic_stability_control"] == "Standard"
    assert row["nhtsa_forward_collision_warning"] == "Optional"
    assert row["nhtsa_lane_departure_warning"] == "No"
    assert row["safercar_authority_source_sha256"]
    assert row["safercar_authority_fields"].split(";")[:3]
    feature_payload = json.loads(row["safercar_feature_payload_json"])
    assert feature_payload["NHTSA_FCW_EVALUATION"] == "Meets Performance Criteria"
    test_refs = json.loads(row["safercar_test_reference_payload_json"])
    assert test_refs["FRNT_TEST_NO"] == "91234"
    injury_metrics = json.loads(row["safercar_injury_metric_payload_json"])
    assert injury_metrics == {
        "CHEST_DEFL_DRIV": "22.4",
        "HIC15_DRIV": "277",
        "POLE_HIC_36_DRIV": "144.0",
    }
    applied_rows = list(csv.DictReader((outdir / "authoritative_applied_rows.csv").open()))
    assert applied_rows[0]["injury_metric_field_count"] == "3"

    overrides = list(csv.DictReader((outdir / "authoritative_overrides.csv").open()))
    assert any(item["db_column"] == "rollover_rating" for item in overrides)


def test_deep_safercar_analysis_writes_feature_and_test_reference_artifacts(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "metadata.sqlite"
    csv_path = tmp_path / "Safercar_data.csv"
    outdir = tmp_path / "deep"
    _seed_overlay(db_path)
    _write_safercar_csv(csv_path)

    summary = safercar_db_compare.write_deep_analysis_artifacts(
        db_path=db_path,
        safercar_csv=csv_path,
        outdir=outdir,
        top_only=True,
    )

    assert summary["matched_feature_rows"] == 1
    assert summary["matched_test_reference_rows"] == 1
    assert summary["matched_injury_metric_rows"] == 1
    feature_rows = list(csv.DictReader((outdir / "consumer_feature_candidates.csv").open()))
    assert json.loads(feature_rows[0]["feature_payload_json"])["NHTSA_BACKUP_CAMERA"] == "Standard"
    test_ref_rows = list(csv.DictReader((outdir / "test_reference_candidates.csv").open()))
    assert json.loads(test_ref_rows[0]["test_reference_payload_json"])["POLE_TEST_NO"] == "91236"
    injury_rows = list(csv.DictReader((outdir / "injury_metric_candidates.csv").open()))
    assert json.loads(injury_rows[0]["injury_metric_payload_json"])["HIC15_DRIV"] == "277"
    profile_rows = list(csv.DictReader((outdir / "field_value_profile.csv").open()))
    assert any(row["safercar_field"] == "NHTSA_FCW_EVALUATION" for row in profile_rows)


def test_apply_safercar_authority_skips_malformed_shifted_values(tmp_path: Path) -> None:
    db_path = tmp_path / "metadata.sqlite"
    csv_path = tmp_path / "Safercar_data.csv"
    outdir = tmp_path / "authority"
    _seed_overlay(db_path)
    csv_path.write_text(
        "MODEL_YR,MAKE,MODEL,BODY_STYLE,VEHICLE_TYPE,DRIVE_TRAIN,PRODUCTION_RELEASE,"
        "OVERALL_STARS,OVERALL_FRNT_STARS,OVERALL_SIDE_STARS,STATIC_STABI_FACTOR,TIP,"
        "ROLLOVER_POSSIBILITY,ROLLOVER_STARS,ROLL_SAFETY_CONCERN,NHTSA_BACKUP_CAMERA,"
        "FRNT_TEST_NO,FRNT_VIN,"
        "SIDE_TEST_NO,POLE_TEST_NO\n"
        "2019,TOYOTA,RAV4,SUV,MPV,AWD,1,5,4,5,0.191,1.19,2058.73600,"
        "4,No Tip,4,5,not-a-vin,287.5,751.5\n",
        encoding="utf-8",
    )

    safercar_db_compare.apply_safercar_authority_to_db(
        db_path=db_path,
        safercar_csv=csv_path,
        outdir=outdir,
        generated_at="2026-06-30T12:00:00+00:00",
    )

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    row = con.execute(
        "select * from nhtsa_rating_match_candidates where row_key='10704::1'"
    ).fetchone()
    assert row["rollover_possibility"] == "0.191"
    assert row["static_stability_factor"] == "1.19"
    assert row["dynamic_tip_result"] == "No Tip"
    feature_payload = json.loads(row["safercar_feature_payload_json"])
    assert "NHTSA_BACKUP_CAMERA" not in feature_payload
    test_refs = json.loads(row["safercar_test_reference_payload_json"])
    assert test_refs == {}



def test_apply_safercar_authority_normalizes_not_rated_placeholders(tmp_path: Path) -> None:
    db_path = tmp_path / "metadata.sqlite"
    csv_path = tmp_path / "Safercar_data.csv"
    outdir = tmp_path / "authority_normalized"
    _seed_overlay(db_path)
    csv_path.write_text(
        "MODEL_YR,MAKE,MODEL,BODY_STYLE,VEHICLE_TYPE,DRIVE_TRAIN,PRODUCTION_RELEASE,"
        "OVERALL_STARS,OVERALL_FRNT_STARS,OVERALL_SIDE_STARS,FRNT_DRIV_STARS,"
        "FRNT_PASS_STARS,STATIC_STABI_FACTOR,TIP,ROLLOVER_POSSIBILITY,ROLLOVER_STARS,"
        "COMB_REAR_STAR\n"
        "2019,TOYOTA,RAV4,SUV,MPV,AWD,1,Not Rated,Not Rated,Not Rated,5,0,"
        "0,N,0,Not Rated,0\n",
        encoding="utf-8",
    )

    safercar_db_compare.apply_safercar_authority_to_db(
        db_path=db_path,
        safercar_csv=csv_path,
        outdir=outdir,
    )

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    row = con.execute(
        "select * from nhtsa_rating_match_candidates where row_key='10704::1'"
    ).fetchone()
    assert row["overall_rating"] == "Not Rated"
    assert row["overall_front_crash_rating"] == "Not Rated"
    assert row["overall_side_crash_rating"] == "Not Rated"
    assert row["front_crash_driver_side_rating"] == "5"
    assert row["front_crash_passenger_side_rating"] == "Not Rated"
    assert row["combined_side_barrier_and_pole_rating_rear"] == "Not Rated"
    assert row["rollover_rating"] == "Not Rated"
    assert row["rollover_possibility"] is None
    assert row["safercar_rollover_possibility"] is None
    assert row["static_stability_factor"] is None
    assert row["dynamic_tip_result"] is None
    assert row["safercar_dynamic_tip_result"] is None

    rating_payload = json.loads(row["safercar_rating_payload_json"])
    assert rating_payload["FRNT_PASS_STARS"] == "Not Rated"
    assert "ROLLOVER_POSSIBILITY" not in rating_payload
    assert "STATIC_STABI_FACTOR" not in rating_payload
    assert "TIP" not in rating_payload
