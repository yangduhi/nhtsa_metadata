from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_DB = Path("D:/vscode/nhtsa_metadata/data/nhtsa_test_metadata_2011.sqlite")
DEFAULT_SAFERCAR_CSV = Path(
    "D:/nhtsa_downloads/official_sources/safercar_20260630/Safercar_data.csv"
)
DEFAULT_OUTDIR = Path("D:/vscode/nhtsa_metadata/artifacts/safercar_db_compare")
RATING_CANDIDATE_TABLE = "nhtsa_rating_match_candidates"

FIELD_PAIRS = [
    ("overall_rating", "OVERALL_STARS"),
    ("overall_front_crash_rating", "OVERALL_FRNT_STARS"),
    ("front_crash_driver_side_rating", "FRNT_DRIV_STARS"),
    ("front_crash_passenger_side_rating", "FRNT_PASS_STARS"),
    ("overall_side_crash_rating", "OVERALL_SIDE_STARS"),
    ("side_crash_driver_side_rating", "SIDE_DRIV_STARS"),
    ("side_crash_passenger_side_rating", "SIDE_PASS_STARS"),
    ("side_barrier_rating_overall", "SIDE_BARRIER_STAR"),
    ("combined_side_barrier_and_pole_rating_front", "COMB_FRNT_STAR"),
    ("combined_side_barrier_and_pole_rating_rear", "COMB_REAR_STAR"),
    ("side_pole_crash_rating", "SIDE_POLE_STARS"),
    ("rollover_rating", "ROLLOVER_STARS"),
    ("rollover_possibility", "ROLLOVER_POSSIBILITY"),
    ("dynamic_tip_result", "TIP"),
    ("static_stability_factor", "STATIC_STABI_FACTOR"),
    ("safercar_dynamic_tip_result", "TIP"),
    ("safercar_rollover_possibility", "ROLLOVER_POSSIBILITY"),
    ("rollover_stars", "ROLLOVER_STARS"),
    ("roll_safety_concern", "ROLL_SAFETY_CONCERN"),
    ("roll_foot_notes", "ROLL_FOOT_NOTES"),
]

OFFICIAL_ROLLOVER_ADOPT_FIELDS = {
    "static_stability_factor": "STATIC_STABI_FACTOR",
    "safercar_dynamic_tip_result": "TIP",
    "safercar_rollover_possibility": "ROLLOVER_POSSIBILITY",
    "rollover_stars": "ROLLOVER_STARS",
    "roll_safety_concern": "ROLL_SAFETY_CONCERN",
    "roll_foot_notes": "ROLL_FOOT_NOTES",
}


SAFERCAR_AUTHORITATIVE_FIELD_MAP = {
    "overall_rating": "OVERALL_STARS",
    "overall_front_crash_rating": "OVERALL_FRNT_STARS",
    "front_crash_driver_side_rating": "FRNT_DRIV_STARS",
    "front_crash_passenger_side_rating": "FRNT_PASS_STARS",
    "overall_side_crash_rating": "OVERALL_SIDE_STARS",
    "side_crash_driver_side_rating": "SIDE_DRIV_STARS",
    "side_crash_passenger_side_rating": "SIDE_PASS_STARS",
    "side_barrier_rating_overall": "SIDE_BARRIER_STAR",
    "combined_side_barrier_and_pole_rating_front": "COMB_FRNT_STAR",
    "combined_side_barrier_and_pole_rating_rear": "COMB_REAR_STAR",
    "side_pole_crash_rating": "SIDE_POLE_STARS",
    "rollover_rating": "ROLLOVER_STARS",
    "rollover_possibility": "ROLLOVER_POSSIBILITY",
    "dynamic_tip_result": "TIP",
    "nhtsa_electronic_stability_control": "NHTSA_ESC",
    "nhtsa_forward_collision_warning": "NHTSA_FRNT_COLLISION_WARNING",
    "nhtsa_lane_departure_warning": "NHTSA_LANE_DEPARTURE_WARNING",
    **OFFICIAL_ROLLOVER_ADOPT_FIELDS,
}

SAFERCAR_AUTHORITY_COLUMNS = {
    "safercar_authority_applied_at": "TEXT",
    "safercar_authority_source_file": "TEXT",
    "safercar_authority_source_sha256": "TEXT",
    "safercar_authority_source_row_index": "TEXT",
    "safercar_authority_fields": "TEXT",
    "safercar_authority_overrides_json": "TEXT",
    "safercar_rating_payload_json": "TEXT",
    "safercar_feature_payload_json": "TEXT",
    "safercar_test_reference_payload_json": "TEXT",
    "safercar_injury_metric_payload_json": "TEXT",
}

SAFERCAR_RATING_PAYLOAD_FIELDS = [
    "OVERALL_STARS",
    "OVERALL_FRNT_STARS",
    "FRNT_DRIV_STARS",
    "FRNT_PASS_STARS",
    "FRNT_SAFETY_CONCERN_DRIV",
    "FRNT_SAFETY_CONCERN_PASS",
    "FRNT_FOOT_NOTES",
    "FRNT_FOOT_NOTES_PASS",
    "SIDE_DRIV_STARS",
    "SIDE_PASS_STARS",
    "SIDE_BARRIER_STAR",
    "COMB_FRNT_STAR",
    "COMB_REAR_STAR",
    "SIDE_SAFETY_CONCERN_DRIV",
    "SIDE_SAFETY_CONCERN_PASS",
    "SIDE_FOOT_NOTES",
    "SIDE_FOOT_NOTES_PASS",
    "OVERALL_SIDE_STARS",
    "SIDE_POLE_STARS",
    "POLE_SAFETY_CONCERN",
    "POLE_FOOT_NOTES",
    "ROLLOVER_POSSIBILITY",
    "STATIC_STABI_FACTOR",
    "TIP",
    "ROLL_SAFETY_CONCERN",
    "ROLL_FOOT_NOTES",
    "ROLLOVER_STARS",
]

SAFERCAR_FEATURE_FIELDS = [
    "BLIND_SPOT_DETECTION",
    "ABS",
    "FRNT_COLLISION_WARNING",
    "NHTSA_FRNT_COLLISION_WARNING",
    "NHTSA_FCW_EVALUATION",
    "LANE_DEPARTURE_WARNING",
    "NHTSA_LANE_DEPARTURE_WARNING",
    "NHTSA_LDW_EVALUATION",
    "CRASH_IMMINENT_BRAKE",
    "NHTSA_CRASH_IMMINENT_BRAKE",
    "NHTSA_CIB_EVALUATION",
    "DYNAMIC_BRAKE_SUPPORT",
    "NHTSA_DYNAMIC_BRAKE_SUPPORT",
    "NHTSA_DBS_EVALUATION",
    "NHTSA_ESC",
    "NHTSA_BACKUP_CAMERA",
    "BACKUP_CAMERA",
]

SAFERCAR_TEST_REFERENCE_FIELDS = [
    "FRNT_TEST_NO",
    "FRNT_VIN",
    "FRNT_TESTED_WITH",
    "SIDE_TEST_NO",
    "SIDE_VIN",
    "SIDE_TESTED_WITH",
    "POLE_TEST_NO",
    "POLE_VIN",
    "POLE_TESTED_WITH",
]

SAFERCAR_INJURY_METRIC_FIELDS = [
    "HIC15_DRIV",
    "CHEST_DEFL_DRIV",
    "LEFT_FEMUR_DRIV",
    "RIGHT_FEMUR_DRIV",
    "NIJ_DRIV",
    "NECK_TENS_DRIV",
    "NET_COMP_DRIV",
    "HIC15_PASS",
    "CHEST_DEFL_PASS",
    "LEFT_FEMUR_PASS",
    "RIGHT_FEMUR_PASS",
    "NIJ_PASS",
    "NECK_TENS_PASS",
    "NET_COMP_PASS",
    "SIDE_HIC_36_DRIV",
    "RIB_DEFLECTION_DRIV",
    "ABDOMEN_FORCE_DRIV",
    "SYMPHYSIS_FORCE_DRIV",
    "SIDE_HIC_36_PASS",
    "PELVIC_FORCE_PASS",
    "POLE_HIC_36_DRIV",
    "PELVIC_FORCE",
]

SAFERCAR_STAR_FIELDS = {
    "OVERALL_STARS",
    "OVERALL_FRNT_STARS",
    "FRNT_DRIV_STARS",
    "FRNT_PASS_STARS",
    "OVERALL_SIDE_STARS",
    "SIDE_DRIV_STARS",
    "SIDE_PASS_STARS",
    "SIDE_BARRIER_STAR",
    "COMB_FRNT_STAR",
    "COMB_REAR_STAR",
    "SIDE_POLE_STARS",
    "ROLLOVER_STARS",
}

SAFERCAR_NHTSA_FEATURE_STATUS_FIELDS = {
    "NHTSA_ESC",
    "NHTSA_FRNT_COLLISION_WARNING",
    "NHTSA_LANE_DEPARTURE_WARNING",
    "NHTSA_CRASH_IMMINENT_BRAKE",
    "NHTSA_DYNAMIC_BRAKE_SUPPORT",
    "NHTSA_BACKUP_CAMERA",
}

SAFERCAR_NHTSA_FEATURE_STATUSES = {
    "NO",
    "STANDARD",
    "OPTIONAL",
    "STANDARD & OPTIONAL",
    "NOT AVAILABLE",
    "STANARD",
    "TBD",
}

SAFERCAR_NHTSA_EVALUATION_FIELDS = {
    "NHTSA_FCW_EVALUATION",
    "NHTSA_LDW_EVALUATION",
    "NHTSA_CIB_EVALUATION",
    "NHTSA_DBS_EVALUATION",
}

REQUIRED_OVERLAY_COLUMNS = {
    "row_key",
    "test_no",
    "source_vehicle_no",
    "db_make",
    "db_model",
    "db_model_year",
    "db_body_type",
    "db_body_style",
    "match_confidence",
    "candidate_rank",
    "candidate_score",
    "rating_vehicle_id",
    "rating_vehicle_description",
}

SAFERCAR_KEY_FIELDS = ("MODEL_YR", "MAKE", "MODEL")
VARIANT_SELECTION_FIELDS = ("DRIVE_TRAIN", "BODY_STYLE", "PRODUCTION_RELEASE", "VEHICLE_TYPE")


def clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def upper_clean(value: Any) -> str:
    return clean(value).upper()


def norm_text(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", upper_clean(value))


def repair_safercar_row(row: dict[str, str]) -> None:
    """Repair observed Safercar row shifts while preserving raw-field conservatism."""

    risk = clean(row.get("ROLLOVER_POSSIBILITY"))
    ssf = clean(row.get("STATIC_STABI_FACTOR"))
    tip = clean(row.get("TIP"))
    concern = clean(row.get("ROLL_SAFETY_CONCERN"))
    if (
        not _number_in_range(risk, 0, 1)
        and _number_in_range(ssf, 0, 1)
        and _number_in_range(tip, 0.5, 3)
        and upper_clean(concern) in {"TIP", "NO TIP"}
    ):
        row["ROLLOVER_POSSIBILITY"] = ssf
        row["STATIC_STABI_FACTOR"] = tip
        row["TIP"] = concern
        row["ROLL_SAFETY_CONCERN"] = ""


def _number_in_range(value: Any, low: float, high: float) -> bool:
    try:
        number = float(clean(value))
    except ValueError:
        return False
    return low < number < high


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safercar_key(year: Any, make: Any, model: Any) -> tuple[str, str, str]:
    return (clean(year), norm_text(make), norm_text(model))


def load_safercar_rows(path: Path) -> tuple[list[dict[str, str]], list[str], str]:
    raw = path.read_text(encoding="utf-8-sig")
    sample = raw[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t|")
    except csv.Error:
        dialect = csv.excel
    rows: list[dict[str, str]] = []
    reader = csv.DictReader(raw.splitlines(), dialect=dialect)
    fieldnames = [str(field or "").strip() for field in (reader.fieldnames or [])]
    for row_index, raw_row in enumerate(reader, start=1):
        row = {str(key or "").strip().upper(): clean(value) for key, value in raw_row.items()}
        repair_safercar_row(row)
        row["__source_row_index"] = str(row_index)
        rows.append(row)
    return rows, fieldnames, sha256_file(path)


def index_safercar_rows(
    rows: list[dict[str, str]],
) -> dict[tuple[str, str, str], list[dict[str, str]]]:
    index: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        key = safercar_key(row.get("MODEL_YR"), row.get("MAKE"), row.get("MODEL"))
        if all(key):
            index.setdefault(key, []).append(row)
    return index


def overlay_columns(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({RATING_CANDIDATE_TABLE})").fetchall()
    return {str(row[1]) for row in rows}


def overlay_rows(db_path: Path, *, top_only: bool = False) -> list[sqlite3.Row]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    columns = overlay_columns(con)
    missing = sorted(REQUIRED_OVERLAY_COLUMNS - columns)
    if missing:
        raise RuntimeError(f"{RATING_CANDIDATE_TABLE} missing required columns: {missing}")
    select_columns = sorted(columns)
    where = "where candidate_rank = 1" if top_only else ""
    order_by = "order by test_no, source_vehicle_no, row_key, candidate_rank, rating_vehicle_id"
    sql = f"select {', '.join(select_columns)} from {RATING_CANDIDATE_TABLE} {where} {order_by}"
    return list(con.execute(sql).fetchall())


def row_get(row: sqlite3.Row, key: str) -> Any:
    return row[key] if key in row.keys() else None


def select_safercar_variant(
    candidates: list[dict[str, str]], rating_vehicle_description: str
) -> tuple[dict[str, str] | None, int, list[str]]:
    if not candidates:
        return None, 0, []
    description = upper_clean(rating_vehicle_description)
    best_row: dict[str, str] | None = None
    best_score = -1
    best_reasons: list[str] = []
    for row in candidates:
        score, reasons = safercar_variant_score(row, description)
        if score > best_score:
            best_row = row
            best_score = score
            best_reasons = reasons
    return best_row, max(best_score, 0), best_reasons


def safercar_variant_score(row: dict[str, str], description: str) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    drive = upper_clean(row.get("DRIVE_TRAIN"))
    for token in ("AWD", "FWD", "RWD", "4WD", "4X2", "4X4"):
        if token and token in drive and token in description:
            score += 20
            reasons.append(f"drive:{token}")
            break
    release = upper_clean(row.get("PRODUCTION_RELEASE"))
    release_reason = production_release_reason(release, description)
    if release_reason:
        score += 15
        reasons.append(release_reason)
    body = upper_clean(row.get("BODY_STYLE"))
    if body and body in description:
        score += 5
        reasons.append(f"body:{body}")
    if release and f" RELEASE {release}" in description:
        score += 3
        reasons.append(f"release:{release}")
    return score, reasons


def production_release_reason(release: str, description: str) -> str:
    if not release:
        return ""
    if "LATER RELEASE" in description or "LATE RELEASE" in description:
        return "release:LATER" if release in {"2", "LATER", "LATE"} else ""
    if "EARLY RELEASE" in description:
        return "release:EARLY" if release in {"1", "EARLY"} else ""
    return ""


def values_equal(left: Any, right: Any) -> bool:
    left_text = clean(left)
    right_text = clean(right)
    if left_text == "" and right_text == "":
        return True
    if left_text == "" or right_text == "":
        return False
    try:
        return abs(float(left_text) - float(right_text)) < 1e-9
    except ValueError:
        return left_text.casefold() == right_text.casefold()


def compare_row(
    row: sqlite3.Row,
    safercar_index: dict[tuple[str, str, str], list[dict[str, str]]],
) -> tuple[dict[str, str], list[dict[str, str]]]:
    key = safercar_key(
        row_get(row, "db_model_year"),
        row_get(row, "db_make"),
        row_get(row, "db_model"),
    )
    variants = safercar_index.get(key, [])
    selected, variant_score, variant_reasons = select_safercar_variant(
        variants, clean(row_get(row, "rating_vehicle_description"))
    )
    out = base_output_row(row)
    out.update(
        {
            "safercar_key": "|".join(key),
            "safercar_variant_count": str(len(variants)),
            "selected_safercar_row_index": clean((selected or {}).get("__source_row_index")),
            "selected_variant_score": str(variant_score),
            "selected_variant_reasons": ";".join(variant_reasons),
        }
    )
    conflicts: list[dict[str, str]] = []
    adoptable_fields: list[str] = []
    if selected is None:
        out["adoption_status"] = "NO_CSV_MATCH"
        out["adoptable_fields"] = ""
        populate_selected_csv_fields(out, {})
        return out, conflicts

    populate_selected_csv_fields(out, selected)
    for db_column, csv_field in FIELD_PAIRS:
        db_value = row_get(row, db_column)
        csv_value = selected.get(csv_field)
        if (
            clean(db_value)
            and meaningful_csv_value(csv_field, csv_value, selected)
            and not values_equal(db_value, csv_value)
        ):
            conflicts.append(
                {
                    **base_output_row(row),
                    "field_pair": f"{db_column}_vs_{csv_field}",
                    "db_value": clean(db_value),
                    "safercar_value": clean(csv_value),
                    "selected_safercar_row_index": clean(selected.get("__source_row_index")),
                    "selected_variant_reasons": ";".join(variant_reasons),
                }
            )
    for db_column, csv_field in OFFICIAL_ROLLOVER_ADOPT_FIELDS.items():
        normalized_value = normalized_authoritative_csv_value(
            csv_field, selected.get(csv_field)
        )
        if (
            normalized_value is not NO_NORMALIZED_VALUE
            and normalized_value is not None
            and not clean(row_get(row, db_column))
        ):
            adoptable_fields.append(db_column)

    out["adoptable_fields"] = ";".join(adoptable_fields)
    if conflicts:
        out["adoption_status"] = "REVIEW_CONFLICT"
    elif adoptable_fields:
        out["adoption_status"] = "READY_OFFICIAL_ENRICHMENT"
    else:
        out["adoption_status"] = "ALREADY_ALIGNED"
    return out, conflicts


def base_output_row(row: sqlite3.Row) -> dict[str, str]:
    return {
        "row_key": clean(row_get(row, "row_key")),
        "test_no": clean(row_get(row, "test_no")),
        "source_vehicle_no": clean(row_get(row, "source_vehicle_no")),
        "candidate_rank": clean(row_get(row, "candidate_rank")),
        "match_confidence": clean(row_get(row, "match_confidence")),
        "db_make": clean(row_get(row, "db_make")),
        "db_model": clean(row_get(row, "db_model")),
        "db_model_year": clean(row_get(row, "db_model_year")),
        "rating_vehicle_id": clean(row_get(row, "rating_vehicle_id")),
        "rating_vehicle_description": clean(row_get(row, "rating_vehicle_description")),
    }


def populate_selected_csv_fields(out: dict[str, str], row: dict[str, str]) -> None:
    output_names = {
        "MODEL_YR": "model_yr_csv",
        "MAKE": "make_csv",
        "MODEL": "model_csv",
        "BODY_STYLE": "body_style_csv",
        "VEHICLE_TYPE": "vehicle_type_csv",
        "DRIVE_TRAIN": "drive_train_csv",
        "PRODUCTION_RELEASE": "production_release_csv",
        "OVERALL_STARS": "overall_stars_csv",
        "OVERALL_FRNT_STARS": "overall_frnt_stars_csv",
        "OVERALL_SIDE_STARS": "overall_side_stars_csv",
        "STATIC_STABI_FACTOR": "static_stability_factor_csv",
        "TIP": "tip_csv",
        "ROLLOVER_POSSIBILITY": "rollover_possibility_csv",
        "ROLLOVER_STARS": "rollover_stars_csv",
        "ROLL_SAFETY_CONCERN": "roll_safety_concern_csv",
        "ROLL_FOOT_NOTES": "roll_foot_notes_csv",
    }
    for field, output_name in output_names.items():
        out[output_name] = clean(row.get(field))


def field_coverage_rows(
    safercar_rows: list[dict[str, str]], fieldnames: list[str], db_rows: list[sqlite3.Row]
) -> list[dict[str, str]]:
    mapped_db_by_csv = {csv_field: db_column for db_column, csv_field in FIELD_PAIRS}
    rows: list[dict[str, str]] = []
    for field in fieldnames:
        field_upper = field.upper()
        csv_non_empty = sum(1 for row in safercar_rows if clean(row.get(field_upper)))
        db_column = mapped_db_by_csv.get(field_upper, "")
        db_non_empty = (
            sum(1 for row in db_rows if clean(row_get(row, db_column))) if db_column else 0
        )
        rows.append(
            {
                "safercar_field": field_upper,
                "csv_non_empty_rows": str(csv_non_empty),
                "mapped_db_column": db_column,
                "db_non_empty_rows": str(db_non_empty) if db_column else "",
                "recommended_action": recommended_action(field_upper, db_column),
            }
        )
    return rows


def recommended_action(field: str, db_column: str) -> str:
    if field in OFFICIAL_ROLLOVER_ADOPT_FIELDS.values():
        return "ADOPT_TO_OFFICIAL_ROLLOVER_OVERLAY"
    if field in set(SAFERCAR_AUTHORITATIVE_FIELD_MAP.values()):
        return "SAFERCAR_AUTHORITATIVE_DB_OVERWRITE"
    if db_column:
        return "CROSS_CHECK_EXISTING_SAFETY_RATING_FIELD"
    if field in {"MAKE", "MODEL", "MODEL_YR", *VARIANT_SELECTION_FIELDS}:
        return "USE_FOR_VARIANT_DISAMBIGUATION"
    if field in SAFERCAR_TEST_REFERENCE_FIELDS:
        return "OFFICIAL_RATING_TEST_REFERENCE"
    if field.startswith("NHTSA_") or field in {
        "BLIND_SPOT_DETECTION",
        "FRNT_COLLISION_WARNING",
        "LANE_DEPARTURE_WARNING",
        "CRASH_IMMINENT_BRAKE",
        "DYNAMIC_BRAKE_SUPPORT",
        "NHTSA_ESC",
        "ABS",
    }:
        return "OPTIONAL_CONSUMER_FEATURE_OVERLAY"
    if field in SAFERCAR_INJURY_METRIC_FIELDS or any(
        token in field for token in ("HIC", "CHEST", "FEMUR", "NECK", "PELVIS")
    ):
        return "REFERENCE_ONLY_TEST_RESULT_METRIC"
    return "REFERENCE_ONLY"


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def compare_safercar_to_db(
    *,
    db_path: Path,
    safercar_csv: Path,
    outdir: Path,
    top_only: bool = False,
) -> dict[str, Any]:
    safercar_rows, fieldnames, csv_sha = load_safercar_rows(safercar_csv)
    safercar_index = index_safercar_rows(safercar_rows)
    db_rows = overlay_rows(db_path, top_only=top_only)
    compared: list[dict[str, str]] = []
    conflicts: list[dict[str, str]] = []
    for row in db_rows:
        compared_row, row_conflicts = compare_row(row, safercar_index)
        compared.append(compared_row)
        conflicts.extend(row_conflicts)

    coverage = field_coverage_rows(safercar_rows, fieldnames, db_rows)
    status_counts = Counter(row["adoption_status"] for row in compared)
    matched_rows = [row for row in compared if row["adoption_status"] != "NO_CSV_MATCH"]
    missing_rows = [row for row in compared if row["adoption_status"] == "NO_CSV_MATCH"]
    outdir.mkdir(parents=True, exist_ok=True)
    adoption_path = outdir / "adoption_candidates.csv"
    conflict_path = outdir / "conflicts.csv"
    coverage_path = outdir / "field_coverage.csv"
    missing_path = outdir / "missing_csv_matches.csv"
    summary_path = outdir / "summary.json"
    write_csv(adoption_path, matched_rows, adoption_fieldnames())
    write_csv(conflict_path, conflicts, conflict_fieldnames())
    write_csv(coverage_path, coverage, coverage_fieldnames())
    write_csv(missing_path, missing_rows, adoption_fieldnames())
    summary: dict[str, Any] = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "db_path": str(db_path),
        "safercar_csv": str(safercar_csv),
        "safercar_csv_sha256": csv_sha,
        "safercar_rows": len(safercar_rows),
        "safercar_field_count": len(fieldnames),
        "safercar_key_count": len(safercar_index),
        "candidate_rows": len(db_rows),
        "matched_candidate_rows": len(matched_rows),
        "missing_csv_match_rows": len(missing_rows),
        "conflict_rows": len(conflicts),
        "adoption_status_counts": dict(status_counts),
        "outputs": {
            "adoption_candidates_csv": str(adoption_path),
            "conflicts_csv": str(conflict_path),
            "field_coverage_csv": str(coverage_path),
            "missing_csv_matches_csv": str(missing_path),
            "summary_json": str(summary_path),
        },
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown_report(outdir / "README.md", summary, coverage, conflicts)
    return summary


def adoption_fieldnames() -> list[str]:
    return [
        "adoption_status",
        "adoptable_fields",
        "row_key",
        "test_no",
        "source_vehicle_no",
        "candidate_rank",
        "match_confidence",
        "db_make",
        "db_model",
        "db_model_year",
        "rating_vehicle_id",
        "rating_vehicle_description",
        "safercar_key",
        "safercar_variant_count",
        "selected_safercar_row_index",
        "selected_variant_score",
        "selected_variant_reasons",
        "static_stability_factor_csv",
        "tip_csv",
        "rollover_possibility_csv",
        "rollover_stars_csv",
        "roll_safety_concern_csv",
        "roll_foot_notes_csv",
        "overall_stars_csv",
        "overall_frnt_stars_csv",
        "overall_side_stars_csv",
        "drive_train_csv",
        "body_style_csv",
        "vehicle_type_csv",
        "production_release_csv",
    ]


def conflict_fieldnames() -> list[str]:
    return [
        "field_pair",
        "db_value",
        "safercar_value",
        "row_key",
        "test_no",
        "source_vehicle_no",
        "candidate_rank",
        "match_confidence",
        "db_make",
        "db_model",
        "db_model_year",
        "rating_vehicle_id",
        "rating_vehicle_description",
        "selected_safercar_row_index",
        "selected_variant_reasons",
    ]


def coverage_fieldnames() -> list[str]:
    return [
        "safercar_field",
        "csv_non_empty_rows",
        "mapped_db_column",
        "db_non_empty_rows",
        "recommended_action",
    ]


def write_markdown_report(
    path: Path,
    summary: dict[str, Any],
    coverage: list[dict[str, str]],
    conflicts: list[dict[str, str]],
) -> None:
    actions = Counter(row["recommended_action"] for row in coverage)
    conflict_pairs = Counter(row["field_pair"] for row in conflicts)
    lines = [
        "# Safercar CSV ↔ local DB comparison",
        "",
        "## Summary",
        "",
        f"- Safercar rows: {summary['safercar_rows']}",
        f"- Safercar fields: {summary['safercar_field_count']}",
        f"- DB candidate rows compared: {summary['candidate_rows']}",
        f"- Matched candidate rows: {summary['matched_candidate_rows']}",
        f"- Missing CSV matches: {summary['missing_csv_match_rows']}",
        f"- Conflict rows: {summary['conflict_rows']}",
        "",
        "## Adoption status counts",
        "",
    ]
    for key, value in sorted(summary["adoption_status_counts"].items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Field action counts", ""])
    for key, value in sorted(actions.items()):
        lines.append(f"- {key}: {value}")
    if conflict_pairs:
        lines.extend(["", "## Conflict pairs", ""])
        for key, value in sorted(conflict_pairs.items()):
            lines.append(f"- {key}: {value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")




def ensure_safercar_authority_columns(connection: sqlite3.Connection) -> None:
    existing = {
        str(row[1])
        for row in connection.execute(f"PRAGMA table_info({RATING_CANDIDATE_TABLE})")
    }
    for column, sql_type in SAFERCAR_AUTHORITY_COLUMNS.items():
        if column not in existing:
            connection.execute(
                f"ALTER TABLE {RATING_CANDIDATE_TABLE} ADD COLUMN {column} {sql_type}"
            )
    for column in (
        "safercar_source_file",
        "safercar_source_sha256",
        "safercar_source_row_index",
    ):
        if column not in existing:
            connection.execute(f"ALTER TABLE {RATING_CANDIDATE_TABLE} ADD COLUMN {column} TEXT")


NO_NORMALIZED_VALUE = object()


def normalized_authoritative_csv_value(
    field: str, value: Any
) -> str | None | object:
    text_value = clean(value)
    if not text_value:
        return NO_NORMALIZED_VALUE
    upper = upper_clean(text_value)
    if upper in {"N/A", "NA", "TBD", "UNKNOWN"}:
        return NO_NORMALIZED_VALUE
    if field in SAFERCAR_STAR_FIELDS:
        if upper == "0":
            return "Not Rated"
        if upper in {"1", "2", "3", "4", "5", "NOT RATED"}:
            return "Not Rated" if upper == "NOT RATED" else text_value
        return NO_NORMALIZED_VALUE
    if field == "TIP":
        if upper in {"TIP", "NO TIP"}:
            return text_value
        if upper in {"0", "N", "NO", "NOT RATED"}:
            return None
        return NO_NORMALIZED_VALUE
    if field in SAFERCAR_NHTSA_FEATURE_STATUS_FIELDS:
        return text_value if upper in SAFERCAR_NHTSA_FEATURE_STATUSES else NO_NORMALIZED_VALUE
    if field == "ROLL_SAFETY_CONCERN":
        if upper in {"0", "NO TIP", "TIP"}:
            return NO_NORMALIZED_VALUE
        try:
            float(text_value)
        except ValueError:
            return text_value
        return NO_NORMALIZED_VALUE
    if field in {"STATIC_STABI_FACTOR", "ROLLOVER_POSSIBILITY"}:
        try:
            number = float(text_value)
        except ValueError:
            return NO_NORMALIZED_VALUE
        if field == "ROLLOVER_POSSIBILITY":
            if 0 < number < 1:
                return text_value
            if number == 0:
                return None
            return NO_NORMALIZED_VALUE
        if 0.5 <= number <= 3:
            return text_value
        if number == 0:
            return None
        return NO_NORMALIZED_VALUE
    return text_value


def meaningful_csv_value(field: str, value: Any, row: dict[str, str]) -> bool:
    normalized = normalized_authoritative_csv_value(field, value)
    return normalized is not NO_NORMALIZED_VALUE and normalized is not None


def meaningful_payload_value(field: str, value: Any, row: dict[str, str]) -> bool:
    text_value = clean(value)
    if not text_value:
        return False
    upper = upper_clean(text_value)
    if field in SAFERCAR_AUTHORITATIVE_FIELD_MAP.values():
        return meaningful_csv_value(field, value, row)
    if field in SAFERCAR_NHTSA_FEATURE_STATUS_FIELDS:
        return upper in SAFERCAR_NHTSA_FEATURE_STATUSES
    if field in SAFERCAR_NHTSA_EVALUATION_FIELDS:
        return any(
            token in upper
            for token in (
                "CRITERIA",
                "PENDING",
                "FAILED",
                "RESULTS",
                "PASSED",
            )
        )
    if field.endswith("_TEST_NO"):
        return text_value.isdigit() and int(text_value) >= 1000
    if field.endswith("_VIN"):
        return len(text_value) == 17 and text_value.isalnum()
    if field.endswith("_TESTED_WITH"):
        return not _is_number(text_value)
    if field in SAFERCAR_FEATURE_FIELDS:
        return not _is_number(text_value)
    if field in SAFERCAR_INJURY_METRIC_FIELDS:
        return _is_number(text_value)
    return True


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def selected_safercar_row_for_overlay_row(
    row: sqlite3.Row,
    safercar_index: dict[tuple[str, str, str], list[dict[str, str]]],
) -> tuple[dict[str, str] | None, int, list[str]]:
    key = safercar_key(
        row_get(row, "db_model_year"),
        row_get(row, "db_make"),
        row_get(row, "db_model"),
    )
    return select_safercar_variant(
        safercar_index.get(key, []),
        clean(row_get(row, "rating_vehicle_description")),
    )


def normalized_payload_value(field: str, value: Any, row: dict[str, str]) -> str | None:
    if field in SAFERCAR_AUTHORITATIVE_FIELD_MAP.values():
        normalized = normalized_authoritative_csv_value(field, value)
        if normalized is NO_NORMALIZED_VALUE or normalized is None:
            return None
        return str(normalized)
    if not meaningful_payload_value(field, value, row):
        return None
    return clean(value)


def payload_for_fields(row: dict[str, str], fields: list[str]) -> dict[str, str]:
    payload: dict[str, str] = {}
    for field in fields:
        normalized = normalized_payload_value(field, row.get(field), row)
        if normalized is not None:
            payload[field] = normalized
    return payload


def apply_safercar_authority_to_db(
    *,
    db_path: Path,
    safercar_csv: Path,
    outdir: Path,
    top_only: bool = False,
    generated_at: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    safercar_rows, _fieldnames, csv_sha = load_safercar_rows(safercar_csv)
    safercar_index = index_safercar_rows(safercar_rows)
    db_rows = overlay_rows(db_path, top_only=top_only)
    applied_rows: list[dict[str, str]] = []
    override_rows: list[dict[str, str]] = []
    now = generated_at or datetime.now(UTC).replace(microsecond=0).isoformat()
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    ensure_safercar_authority_columns(con)

    for row in db_rows:
        selected, variant_score, variant_reasons = selected_safercar_row_for_overlay_row(
            row, safercar_index
        )
        if selected is None:
            continue
        assignments: dict[str, str | None] = {}
        overrides: list[dict[str, str]] = []
        for db_column, csv_field in SAFERCAR_AUTHORITATIVE_FIELD_MAP.items():
            csv_value = clean(selected.get(csv_field))
            normalized_value = normalized_authoritative_csv_value(csv_field, csv_value)
            if normalized_value is NO_NORMALIZED_VALUE:
                continue
            old_value = clean(row_get(row, db_column))
            new_value = None if normalized_value is None else str(normalized_value)
            assignments[db_column] = new_value
            if old_value and not values_equal(old_value, new_value or ""):
                override = {
                    **base_output_row(row),
                    "db_column": db_column,
                    "safercar_field": csv_field,
                    "old_value": old_value,
                    "new_value": new_value or "",
                    "selected_safercar_row_index": clean(selected.get("__source_row_index")),
                    "selected_variant_score": str(variant_score),
                    "selected_variant_reasons": ";".join(variant_reasons),
                }
                overrides.append(override)
                override_rows.append(override)
        rating_payload = payload_for_fields(selected, SAFERCAR_RATING_PAYLOAD_FIELDS)
        feature_payload = payload_for_fields(selected, SAFERCAR_FEATURE_FIELDS)
        test_reference_payload = payload_for_fields(selected, SAFERCAR_TEST_REFERENCE_FIELDS)
        injury_metric_payload = payload_for_fields(selected, SAFERCAR_INJURY_METRIC_FIELDS)
        if not (
            assignments
            or rating_payload
            or feature_payload
            or test_reference_payload
            or injury_metric_payload
        ):
            continue
        authority_fields = sorted(assignments)
        authority_columns = {
            "safercar_authority_applied_at": now,
            "safercar_authority_source_file": str(safercar_csv),
            "safercar_authority_source_sha256": csv_sha,
            "safercar_authority_source_row_index": clean(selected.get("__source_row_index")),
            "safercar_authority_fields": ";".join(authority_fields),
            "safercar_authority_overrides_json": json.dumps(overrides, ensure_ascii=False),
            "safercar_rating_payload_json": json.dumps(
                rating_payload, ensure_ascii=False, sort_keys=True
            ),
            "safercar_feature_payload_json": json.dumps(
                feature_payload, ensure_ascii=False, sort_keys=True
            ),
            "safercar_test_reference_payload_json": json.dumps(
                test_reference_payload, ensure_ascii=False, sort_keys=True
            ),
            "safercar_injury_metric_payload_json": json.dumps(
                injury_metric_payload, ensure_ascii=False, sort_keys=True
            ),
        }
        if any(field in assignments for field in OFFICIAL_ROLLOVER_ADOPT_FIELDS):
            authority_columns["safercar_source_file"] = str(safercar_csv)
            authority_columns["safercar_source_sha256"] = csv_sha
            authority_columns["safercar_source_row_index"] = clean(
                selected.get("__source_row_index")
            )
        all_assignments = {**assignments, **authority_columns}
        applied_rows.append(
            {
                **base_output_row(row),
                "selected_safercar_row_index": clean(selected.get("__source_row_index")),
                "selected_variant_score": str(variant_score),
                "selected_variant_reasons": ";".join(variant_reasons),
                "fields_applied": ";".join(authority_fields),
                "override_count": str(len(overrides)),
                "feature_field_count": str(len(feature_payload)),
                "test_reference_field_count": str(len(test_reference_payload)),
                "injury_metric_field_count": str(len(injury_metric_payload)),
            }
        )
        if not dry_run:
            set_sql = ", ".join(f"{column} = ?" for column in all_assignments)
            con.execute(
                f"UPDATE {RATING_CANDIDATE_TABLE} SET {set_sql} "
                "WHERE row_key = ? AND rating_vehicle_id = ?",
                [
                    *all_assignments.values(),
                    row_get(row, "row_key"),
                    row_get(row, "rating_vehicle_id"),
                ],
            )
    if not dry_run:
        con.commit()

    outdir.mkdir(parents=True, exist_ok=True)
    applied_path = outdir / "authoritative_applied_rows.csv"
    overrides_path = outdir / "authoritative_overrides.csv"
    summary_path = outdir / "summary_authoritative_apply.json"
    write_csv(applied_path, applied_rows, authoritative_applied_fieldnames())
    write_csv(overrides_path, override_rows, authoritative_override_fieldnames())
    summary = {
        "generated_at": now,
        "dry_run": dry_run,
        "db_path": str(db_path),
        "safercar_csv": str(safercar_csv),
        "safercar_csv_sha256": csv_sha,
        "candidate_rows_scanned": len(db_rows),
        "updated_rows": len(applied_rows),
        "overridden_value_count": len(override_rows),
        "outputs": {
            "authoritative_applied_rows_csv": str(applied_path),
            "authoritative_overrides_csv": str(overrides_path),
            "summary_json": str(summary_path),
        },
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def authoritative_applied_fieldnames() -> list[str]:
    return [
        "row_key",
        "test_no",
        "source_vehicle_no",
        "candidate_rank",
        "match_confidence",
        "db_make",
        "db_model",
        "db_model_year",
        "rating_vehicle_id",
        "rating_vehicle_description",
        "selected_safercar_row_index",
        "selected_variant_score",
        "selected_variant_reasons",
        "fields_applied",
        "override_count",
        "feature_field_count",
        "test_reference_field_count",
        "injury_metric_field_count",
    ]


def authoritative_override_fieldnames() -> list[str]:
    return [
        "db_column",
        "safercar_field",
        "old_value",
        "new_value",
        "row_key",
        "test_no",
        "source_vehicle_no",
        "candidate_rank",
        "match_confidence",
        "db_make",
        "db_model",
        "db_model_year",
        "rating_vehicle_id",
        "rating_vehicle_description",
        "selected_safercar_row_index",
        "selected_variant_score",
        "selected_variant_reasons",
    ]


def write_deep_analysis_artifacts(
    *,
    db_path: Path,
    safercar_csv: Path,
    outdir: Path,
    top_only: bool = True,
) -> dict[str, Any]:
    safercar_rows, fieldnames, csv_sha = load_safercar_rows(safercar_csv)
    safercar_index = index_safercar_rows(safercar_rows)
    db_rows = overlay_rows(db_path, top_only=top_only)
    feature_rows: list[dict[str, str]] = []
    test_reference_rows: list[dict[str, str]] = []
    injury_metric_rows: list[dict[str, str]] = []
    matched = 0
    for row in db_rows:
        selected, score, reasons = selected_safercar_row_for_overlay_row(row, safercar_index)
        if selected is None:
            continue
        matched += 1
        base = {
            **base_output_row(row),
            "selected_safercar_row_index": clean(selected.get("__source_row_index")),
            "selected_variant_score": str(score),
            "selected_variant_reasons": ";".join(reasons),
        }
        feature_payload = payload_for_fields(selected, SAFERCAR_FEATURE_FIELDS)
        if feature_payload:
            feature_rows.append(
                {
                    **base,
                    "feature_payload_json": json.dumps(
                        feature_payload, ensure_ascii=False, sort_keys=True
                    ),
                }
            )
        test_reference_payload = payload_for_fields(selected, SAFERCAR_TEST_REFERENCE_FIELDS)
        if test_reference_payload:
            test_reference_rows.append(
                {
                    **base,
                    "test_reference_payload_json": json.dumps(
                        test_reference_payload, ensure_ascii=False, sort_keys=True
                    ),
                }
            )
        injury_metric_payload = payload_for_fields(selected, SAFERCAR_INJURY_METRIC_FIELDS)
        if injury_metric_payload:
            injury_metric_rows.append(
                {
                    **base,
                    "injury_metric_payload_json": json.dumps(
                        injury_metric_payload, ensure_ascii=False, sort_keys=True
                    ),
                }
            )
    field_profile = safercar_field_value_profile(safercar_rows, fieldnames)
    outdir.mkdir(parents=True, exist_ok=True)
    profile_path = outdir / "field_value_profile.csv"
    features_path = outdir / "consumer_feature_candidates.csv"
    references_path = outdir / "test_reference_candidates.csv"
    injury_path = outdir / "injury_metric_candidates.csv"
    summary_path = outdir / "deep_analysis_summary.json"
    write_csv(profile_path, field_profile, field_profile_fieldnames())
    write_csv(features_path, feature_rows, deep_payload_fieldnames("feature_payload_json"))
    write_csv(
        references_path,
        test_reference_rows,
        deep_payload_fieldnames("test_reference_payload_json"),
    )
    write_csv(
        injury_path,
        injury_metric_rows,
        deep_payload_fieldnames("injury_metric_payload_json"),
    )
    summary = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "db_path": str(db_path),
        "safercar_csv": str(safercar_csv),
        "safercar_csv_sha256": csv_sha,
        "candidate_rows_scanned": len(db_rows),
        "matched_candidate_rows": matched,
        "matched_feature_rows": len(feature_rows),
        "matched_test_reference_rows": len(test_reference_rows),
        "matched_injury_metric_rows": len(injury_metric_rows),
        "outputs": {
            "field_value_profile_csv": str(profile_path),
            "consumer_feature_candidates_csv": str(features_path),
            "test_reference_candidates_csv": str(references_path),
            "injury_metric_candidates_csv": str(injury_path),
            "summary_json": str(summary_path),
        },
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def safercar_field_value_profile(
    safercar_rows: list[dict[str, str]], fieldnames: list[str]
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for field in fieldnames:
        field_upper = field.upper()
        values = [
            clean(row.get(field_upper))
            for row in safercar_rows
            if clean(row.get(field_upper))
        ]
        counter = Counter(values)
        rows.append(
            {
                "safercar_field": field_upper,
                "non_empty_rows": str(len(values)),
                "distinct_values": str(len(counter)),
                "top_values_json": json.dumps(counter.most_common(12), ensure_ascii=False),
                "recommended_action": recommended_action(field_upper, ""),
            }
        )
    return rows


def field_profile_fieldnames() -> list[str]:
    return [
        "safercar_field",
        "non_empty_rows",
        "distinct_values",
        "top_values_json",
        "recommended_action",
    ]


def deep_payload_fieldnames(payload_name: str) -> list[str]:
    return [
        "row_key",
        "test_no",
        "source_vehicle_no",
        "candidate_rank",
        "match_confidence",
        "db_make",
        "db_model",
        "db_model_year",
        "rating_vehicle_id",
        "rating_vehicle_description",
        "selected_safercar_row_index",
        "selected_variant_score",
        "selected_variant_reasons",
        payload_name,
    ]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite metadata DB path")
    parser.add_argument("--safercar-csv", default=str(DEFAULT_SAFERCAR_CSV), help="Safercar CSV")
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR), help="Output artifact directory")
    parser.add_argument(
        "--top-only",
        action="store_true",
        help="Compare only candidate_rank=1 rows",
    )
    parser.add_argument(
        "--apply-authoritative",
        action="store_true",
        help="Update overlay rating fields with authoritative Safercar CSV values",
    )
    parser.add_argument(
        "--deep-analysis",
        action="store_true",
        help="Write additional field/profile/test-reference analysis artifacts",
    )
    parser.add_argument("--generated-at", default=None, help="Timestamp for apply mode")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write apply artifacts without DB update",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.apply_authoritative:
        summary = apply_safercar_authority_to_db(
            db_path=Path(args.db),
            safercar_csv=Path(args.safercar_csv),
            outdir=Path(args.outdir),
            top_only=args.top_only,
            generated_at=args.generated_at,
            dry_run=args.dry_run,
        )
    elif args.deep_analysis:
        summary = write_deep_analysis_artifacts(
            db_path=Path(args.db),
            safercar_csv=Path(args.safercar_csv),
            outdir=Path(args.outdir),
            top_only=args.top_only,
        )
    else:
        summary = compare_safercar_to_db(
            db_path=Path(args.db),
            safercar_csv=Path(args.safercar_csv),
            outdir=Path(args.outdir),
            top_only=args.top_only,
        )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
